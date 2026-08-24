from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from autodev.git_tools import (
    GitError,
    branch_exists,
    branch_head,
    changed_paths_between,
    compute_file_hashes,
    compute_indexed_blob_hashes,
    count_tracked_commits_between,
    current_branch,
    current_head,
    diff_patch_between,
    get_index_changed_paths,
    get_tracked_dirty_paths,
    get_untracked_paths,
    git_output,
    git_status_with_branch,
    name_status_between,
    worktree_registered,
)
from autodev.path_rules import normalize_repo_relative_path
from autodev.planner import PlanningError, load_json


class GitContextError(RuntimeError):
    """État Git de tâche invalide ou incomplet."""


def _is_path_relative_to(path: Path, parent: Path) -> bool:
    """Check if path is a child of parent directory."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _allowed_scope_is_directory(snapshot: GitSnapshot, scope: Path) -> bool:
    """Determine whether an allowed scope is a directory from Git, then filesystem."""
    worktree_path = Path(snapshot.worktree_path)
    scope_text = scope.as_posix()

    try:
        object_type = git_output(
            worktree_path,
            ["cat-file", "-t", f"{snapshot.head}:{scope_text}"],
            cwd=worktree_path,
        )
    except GitError:
        scoped_path = worktree_path / scope
        return scoped_path.is_dir()

    return object_type == "tree"


def path_matches_allowed_scope(snapshot: GitSnapshot, path: Path, allowed_scope: Path) -> bool:
    """Return whether a normalized repo path is inside one normalized allowed scope.

    Exact matches are always allowed. Descendants are allowed only when the
    allowed scope is proven to be a directory from Git HEAD or the filesystem.
    """
    return path == allowed_scope or (
        _allowed_scope_is_directory(snapshot, allowed_scope)
        and _is_path_relative_to(path, allowed_scope)
    )


@dataclass(frozen=True)
class GitSnapshot:
    """Capture précise de l'état Git à un moment donné."""
    head: str
    branch: str
    index_changed: list[str]
    tracked_dirty: list[str]
    untracked: list[str]
    status_porcelain: str
    timestamp_label: str
    worktree_path: str
    file_hashes: dict[str, str] | None = None
    # AC-R22-3: Hashes des blobs indexés, séparés du contenu worktree
    indexed_blob_hashes: dict[str, str] | None = None
    # Chemins affectés par changement de HEAD (commits entre deux HEAD)
    paths_from_head_change: list[str] | None = None


@dataclass(frozen=True)
class GitSnapshotTriple:
    """Trois snapshots pour audit de mutations (avant hooks, après hooks, après processus)."""
    before_hooks: GitSnapshot
    after_hooks: GitSnapshot
    after_process: GitSnapshot


@dataclass(frozen=True)
class ContentFingerprints:
    """Empreintes déterministes du contenu des fichiers.

    Couvre: blob indexé (staged), contenu worktree (dirty), fichiers non suivis.
    Les empreintes permettent de détecter les changements de contenu
    sur des fichiers déjà modifiés avant le début du processus.
    """
    indexed_blob_hashes: dict[str, str] = field(default_factory=dict)
    worktree_content_hashes: dict[str, str] = field(default_factory=dict)
    untracked_file_hashes: dict[str, str] = field(default_factory=dict)
    timestamp_label: str = ""

    def all_hashes(self) -> dict[str, str]:
        """Combine all hashes for comparison.

        Note: This merges categories by path and should only be used for
        detecting presence changes. For comparing distinct categories
        (indexed vs worktree for same path), use separate dictionaries.
        """
        result = {}
        result.update(self.indexed_blob_hashes)
        result.update(self.worktree_content_hashes)
        result.update(self.untracked_file_hashes)
        return result

    def get_hash_with_category(self, path: str) -> tuple[str | None, str]:
        """Get hash for a path with its primary category.

        AC-R22-3: Distinguish between indexed blob, worktree content and untracked.
        Returns (hash, category) where category is 'indexed', 'tracked_dirty', or 'untracked'.
        For files that exist in multiple categories, prefer worktree > untracked > indexed.
        """
        if path in self.worktree_content_hashes:
            return self.worktree_content_hashes[path], "tracked_dirty"
        elif path in self.untracked_file_hashes:
            return self.untracked_file_hashes[path], "untracked"
        elif path in self.indexed_blob_hashes:
            return self.indexed_blob_hashes[path], "indexed"
        else:
            return None, ""

    def get_all_paths_with_categories(self) -> dict[str, tuple[str | None, str]]:
        """Get all paths with their hashes and categories.

        AC-R22-3: Returns dict mapping path -> (hash, category).
        """
        result = {}
        # Collect all unique paths
        all_paths = set()
        all_paths.update(self.indexed_blob_hashes.keys())
        all_paths.update(self.worktree_content_hashes.keys())
        all_paths.update(self.untracked_file_hashes.keys())

        for path in all_paths:
            result[path] = self.get_hash_with_category(path)
        return result


@dataclass(frozen=True)
class ModificationChange:
    """Enregistre une modification détectée entre deux états."""
    path: str
    category: Literal["indexed", "tracked_dirty", "untracked"]
    before_hash: str | None
    after_hash: str | None
    hash_changed: bool
    presence_changed: bool  # Fichier apparu ou disparu


@dataclass(frozen=True)
class ModificationClassification:
    """Classification d'une modification selon son scope autorisé."""
    path: str
    is_allowed: bool  # Chemin dans modified_paths
    is_preexisting: bool  # Fichier dirty avant le début
    is_agent_mutation: bool  # Mutation attribuée à l'agent
    classification: Literal["allowed", "partial", "out_of_scope", "preexisting"] = "out_of_scope"


@dataclass(frozen=True)
class ReconciliationDiagnostic:
    """Diagnostic structuré pour la réconciliation après interruption.

    AC-R11-5: Un diagnostic structuré précède toute reprise.
    AC-R22-9: Toute réconciliation produit des preuves vérifiables.
    """
    has_divergence: bool
    preexisting_dirty_paths: list[str]
    allowed_changes: list[ModificationClassification]
    partial_changes: list[ModificationClassification]
    out_of_scope_changes: list[ModificationClassification]
    content_changes_detected: list[ModificationChange]
    verdict: Literal["safe_to_recover", "requires_review", "request_human"]
    evidence: dict[str, Any] = field(default_factory=dict)

    def can_safely_restore_out_of_scope(self) -> bool:
        """AC-R11-4: Les chemins hors scope peuvent être restaurés si pas d'ambiguïté."""
        if self.verdict == "request_human":
            return False
        if any(ch.hash_changed for ch in self.content_changes_detected
               if ch.path in [oc.path for oc in self.out_of_scope_changes]):
            return False
        return True


@dataclass(frozen=True)
class ExecutionMutationMetadata:
    """Métadonnées optionnelles d'exécution pour corroboration d'attributions.

    Une revendication dans les métadonnées ne constitue pas à elle seule une preuve.
    Elle doit correspondre et corroborer une transition Git réellement observée.
    """
    attempt_id: str | None = None
    agent_claimed_commits: list[str] = field(default_factory=list)
    externally_proven_commits: list[str] = field(default_factory=list)
    agent_claimed_paths: list[str] = field(default_factory=list)
    externally_proven_paths: list[str] = field(default_factory=list)
    agent_claimed_index_transitions: dict[str, str] = field(default_factory=dict)
    externally_proven_index_transitions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MutationAttribution:
    """Attribution d'une mutation à sa source (hook, agent, préexistant, externe).

    L'origine est déterministe et basée sur l'observation de l'état Git,
    en corroboration avec les métadonnées optionnelles.
    """
    path: str
    before_hooks: bool
    hook_mutation: bool
    agent_mutation: bool
    external_mutation: bool
    # Transitions d'index détectées
    hook_index_transition: str | None = None  # "untracked->staged", "dirty->staged", etc.
    agent_index_transition: str | None = None
    # Source prouvée via métadonnées (commit SHA, etc.)
    proven_agent_source: bool = False
    ambiguous_origin: bool = False
    # Origine explicite et déterministe
    origin: Literal["preexisting", "hook", "agent", "external", "indeterminate"] = "indeterminate"


@dataclass(frozen=True)
class CurrentTaskGitState:
    task_id: str
    branch: str
    worktree: Path
    base_commit: str
    produced_commit: str
    modified_paths: list[str]
    name_status: list[str]
    diff_text: str


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except PlanningError as exc:
        raise GitContextError(str(exc)) from exc


def resolve_task_metadata(repo_root: Path, task_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    run_dir = repo_root / ".autodev" / "runs" / task_id
    run_result = load_optional_json(run_dir / "result.json")
    task_record = load_optional_json(run_dir / "task.json")
    return run_dir, run_result, task_record


def resolve_base_commit(task_id: str, run_result: dict[str, Any], task_record: dict[str, Any]) -> str:
    base_commit = run_result.get("base_commit") or task_record.get("base_commit")
    if not isinstance(base_commit, str) or not base_commit.strip():
        raise GitContextError(f"Commit de départ introuvable pour {task_id}.")
    return base_commit


def resolve_worktree(repo_root: Path, task_id: str, run_result: dict[str, Any], task_record: dict[str, Any]) -> Path:
    raw_value = (
        run_result.get("worktree")
        or task_record.get("worktree")
        or str(repo_root / ".autodev" / "worktrees" / task_id)
    )
    return Path(str(raw_value))


def resolve_produced_commit(repo_root: Path, task_id: str, branch: str, base_commit: str) -> str:
    try:
        produced_commit = branch_head(repo_root, branch)
        if count_tracked_commits_between(repo_root, base_commit, branch) <= 0:
            raise GitContextError(f"Aucun commit produit courant détecté pour {task_id}.")
        return produced_commit
    except GitError as exc:
        raise GitContextError(str(exc)) from exc


def build_current_task_git_state(repo_root: Path, task_id: str) -> CurrentTaskGitState:
    branch = f"autodev/{task_id}"
    _, run_result, task_record = resolve_task_metadata(repo_root, task_id)
    base_commit = resolve_base_commit(task_id, run_result, task_record)
    worktree = resolve_worktree(repo_root, task_id, run_result, task_record)
    produced_commit = resolve_produced_commit(repo_root, task_id, branch, base_commit)

    try:
        modified_paths = changed_paths_between(repo_root, base_commit, produced_commit)
        name_status = name_status_between(repo_root, base_commit, produced_commit)
        diff_text = diff_patch_between(repo_root, base_commit, produced_commit)
    except GitError as exc:
        raise GitContextError(str(exc)) from exc

    return CurrentTaskGitState(
        task_id=task_id,
        branch=branch,
        worktree=worktree,
        base_commit=base_commit,
        produced_commit=produced_commit,
        modified_paths=modified_paths,
        name_status=name_status,
        diff_text=diff_text,
    )


def capture_git_snapshot(
    repo_root: Path,
    worktree_path: Path | None = None,
    timestamp_label: str = "",
    capture_file_hashes: bool = True,
    previous_head: str | None = None,
) -> GitSnapshot:
    """Capture une vue détaillée de l'état Git à un moment donné.

    Capture toujours les hashes de fichiers pour détecter les mutations
    de contenu même sur les fichiers déjà dirty (prérequis pour audit
    fiable des mutations de hook vs agent sur état préexistant).

    AC-R22-3: Capture aussi les hashes des blobs indexés séparément du contenu worktree.

    Si previous_head est fourni, capture aussi les chemins affectés
    par le changement de HEAD (commits).
    """
    try:
        if worktree_path is None:
            worktree_path = repo_root

        head = current_head(repo_root, cwd=worktree_path)
        branch = current_branch(repo_root, cwd=worktree_path)
        status = git_status_with_branch(repo_root, cwd=worktree_path)

        index_changed = get_index_changed_paths(repo_root, cwd=worktree_path)
        tracked_dirty = get_tracked_dirty_paths(repo_root, cwd=worktree_path)
        untracked = get_untracked_paths(repo_root, cwd=worktree_path)

        all_dirty_files = index_changed + tracked_dirty + untracked
        file_hashes = compute_file_hashes(worktree_path, all_dirty_files) if capture_file_hashes else None

        # AC-R22-3: Capturer aussi les hashes des blobs indexés
        indexed_blob_hashes = None
        if capture_file_hashes and index_changed:
            try:
                indexed_blob_hashes = compute_indexed_blob_hashes(repo_root, index_changed, cwd=worktree_path)
            except GitError:
                indexed_blob_hashes = None

        # Si HEAD a changé, récupérer les chemins affectés par le changement de commit
        paths_from_head_change: list[str] | None = None
        if previous_head is not None and previous_head != head:
            try:
                paths_from_head_change = changed_paths_between(repo_root, previous_head, head)
            except GitError:
                # Si la comparaison échoue (commits non liés), conserver None
                paths_from_head_change = None

        return GitSnapshot(
            head=head,
            branch=branch,
            index_changed=index_changed,
            tracked_dirty=tracked_dirty,
            untracked=untracked,
            status_porcelain=status,
            timestamp_label=timestamp_label,
            worktree_path=str(worktree_path.resolve()),
            file_hashes=file_hashes,
            indexed_blob_hashes=indexed_blob_hashes,
            paths_from_head_change=paths_from_head_change,
        )
    except GitError as exc:
        raise GitContextError(f"Impossible de capturer l'état Git : {exc}") from exc


def analyze_mutations(
    before_hooks: GitSnapshot,
    after_hooks: GitSnapshot,
    after_process: GitSnapshot,
    metadata: ExecutionMutationMetadata | None = None,
) -> dict[str, MutationAttribution]:
    """Analyse les mutations et les attribue à leur source.

    Distingue:
    - mutations préexistantes (avant hooks)
    - mutations de hook (entre avant_hooks et after_hooks)
    - mutations d'agent (entre after_hooks et after_process)
    - mutations externes (preuve structurée requise, pas de heuristique)

    Les métadonnées optionnelles doivent être corroborées par l'état Git observé.
    Une revendication sans corroboration Git ne produit pas d'attribution prouvée.

    Détecte les transitions d'index et préserve les chemins commits via
    paths_from_head_change. HEAD changé seul ne produit JAMAIS origin=external.
    """
    if metadata is None:
        metadata = ExecutionMutationMetadata()

    attributions: dict[str, MutationAttribution] = {}
    head_changed_before_to_after = before_hooks.head != after_process.head

    # Univers des chemins : visible dans les snapshots + chemins commits
    all_paths = set()
    all_paths.update(before_hooks.index_changed)
    all_paths.update(before_hooks.tracked_dirty)
    all_paths.update(before_hooks.untracked)
    all_paths.update(after_hooks.index_changed)
    all_paths.update(after_hooks.tracked_dirty)
    all_paths.update(after_hooks.untracked)
    all_paths.update(after_process.index_changed)
    all_paths.update(after_process.tracked_dirty)
    all_paths.update(after_process.untracked)

    # Ajouter les chemins affectés par changements de commit
    if after_process.paths_from_head_change:
        all_paths.update(after_process.paths_from_head_change)
    if after_hooks.paths_from_head_change:
        all_paths.update(after_hooks.paths_from_head_change)

    for path in sorted(all_paths):
        before_hooks_dirty = (
            path in before_hooks.index_changed
            or path in before_hooks.tracked_dirty
            or path in before_hooks.untracked
        )
        after_hooks_dirty = (
            path in after_hooks.index_changed
            or path in after_hooks.tracked_dirty
            or path in after_hooks.untracked
        )
        after_process_dirty = (
            path in after_process.index_changed
            or path in after_process.tracked_dirty
            or path in after_process.untracked
        )

        # Déterminer l'état d'index pour détecter les transitions
        before_hooks_state = _get_index_state(path, before_hooks)
        after_hooks_state = _get_index_state(path, after_hooks)
        after_process_state = _get_index_state(path, after_process)

        hook_content_changed = False
        agent_content_changed = False

        if before_hooks.file_hashes is not None and after_hooks.file_hashes is not None:
            before_hash = before_hooks.file_hashes.get(path)
            after_hook_hash = after_hooks.file_hashes.get(path)
            if before_hash is not None and after_hook_hash is not None:
                hook_content_changed = before_hash != after_hook_hash

        if after_hooks.file_hashes is not None and after_process.file_hashes is not None:
            after_hook_hash = after_hooks.file_hashes.get(path)
            after_process_hash = after_process.file_hashes.get(path)
            if after_hook_hash is not None and after_process_hash is not None:
                agent_content_changed = after_hook_hash != after_process_hash

        # Détecter les mutations
        hook_mutation = (not before_hooks_dirty and after_hooks_dirty) or hook_content_changed
        agent_mutation = (not after_hooks_dirty and after_process_dirty) or agent_content_changed

        # Détecter les transitions d'index
        hook_index_transition = _detect_index_transition(before_hooks_state, after_hooks_state)
        agent_index_transition = _detect_index_transition(after_hooks_state, after_process_state)

        # Si une transition d'index est détectée, c'est une mutation
        if hook_index_transition:
            hook_mutation = True
        if agent_index_transition:
            agent_mutation = True

        # Déterminer si le chemin est dans paths_from_head_change (commit détecté)
        path_in_head_change = path in (after_process.paths_from_head_change or [])
        path_in_hook_head_change = path in (after_hooks.paths_from_head_change or [])

        # Détection de commits: si le chemin est dans paths_from_head_change,
        # un commit l'a affecté. Déterminer si c'est hook ou agent.
        if path_in_hook_head_change and not path_in_head_change:
            # Chemin affecté par un commit entre before_hooks et after_hooks => hook mutation
            hook_mutation = True
        elif path_in_head_change and not path_in_hook_head_change:
            # Chemin affecté par un commit entre after_hooks et after_process => agent mutation
            agent_mutation = True

        # Déterminer l'origine avec corroboration Git
        # Priorité: preexisting > hook > external (prouvé) > agent > indeterminate
        origin: Literal["preexisting", "hook", "agent", "external", "indeterminate"] = "indeterminate"
        external_mutation = False
        proven_agent_source = False

        # Distinguer si agent_mutation provient d'un commit ou d'une transition d'index
        agent_mutation_is_from_commit = path_in_head_change and not agent_index_transition
        agent_mutation_is_from_index_transition = agent_index_transition is not None

        if before_hooks_dirty and not hook_mutation and not agent_mutation:
            # Fichier était dirty avant, rien ne l'a touché
            origin = "preexisting"
        elif hook_mutation and not agent_mutation:
            # Hook a modifié, agent ne l'a pas touché
            origin = "hook"
        elif path in metadata.externally_proven_paths:
            # Preuve externe structurée dans métadonnées (override agent_mutation)
            external_mutation = True
            origin = "external"
        elif agent_mutation and agent_mutation_is_from_index_transition:
            # Transition d'index = mutation d'agent directe (staging, etc.)
            # Pas besoin de métadonnées, c'est clairement de l'agent
            if path in metadata.agent_claimed_paths:
                proven_agent_source = True
            origin = "agent"
        elif agent_mutation and agent_mutation_is_from_commit and path in metadata.agent_claimed_paths:
            # Commit + revendication agent dans métadonnées = prouvé
            proven_agent_source = True
            origin = "agent"
        elif agent_mutation and agent_mutation_is_from_commit:
            # Commit sans métadonnées = indeterminate
            # (On ne peut pas distinguer agent d'external sans preuve)
            origin = "indeterminate"
        else:
            # Pas de mutation détectée
            origin = "indeterminate"

        if before_hooks_dirty or hook_mutation or agent_mutation or external_mutation or path_in_head_change:
            attributions[path] = MutationAttribution(
                path=path,
                before_hooks=before_hooks_dirty,
                hook_mutation=hook_mutation,
                agent_mutation=agent_mutation,
                external_mutation=external_mutation,
                hook_index_transition=hook_index_transition,
                agent_index_transition=agent_index_transition,
                proven_agent_source=proven_agent_source,
                origin=origin,
            )

    return attributions


def _get_index_state(path: str, snapshot: GitSnapshot) -> str:
    """Détermine l'état d'index d'un fichier : staged, dirty, untracked, clean."""
    if path in snapshot.index_changed:
        return "staged"
    elif path in snapshot.tracked_dirty:
        return "dirty"
    elif path in snapshot.untracked:
        return "untracked"
    else:
        return "clean"


def _detect_index_transition(from_state: str, to_state: str) -> str | None:
    """Détecte une transition d'état d'index significative."""
    if from_state == to_state:
        return None

    # Transitions significatives
    transitions = {
        ("dirty", "staged"): "dirty->staged",
        ("untracked", "staged"): "untracked->staged",
        ("dirty", "clean"): "dirty->clean",
        ("staged", "clean"): "staged->clean",
        ("untracked", "dirty"): "untracked->dirty",
        ("clean", "dirty"): "clean->dirty",
        ("clean", "untracked"): "clean->untracked",
        ("clean", "staged"): "clean->staged",
    }

    return transitions.get((from_state, to_state))


def capture_git_snapshot_triple(
    repo_root: Path,
    worktree_path: Path | None = None,
) -> GitSnapshotTriple:
    """Capture consécutive des trois snapshots (exemple de structure).

    NOTE: Cette fonction capture les trois snapshots de manière consécutive.
    En production, les captures doivent être effectuées via
    `capture_git_snapshot_triple_with_lifecycle()` pour garantir l'exécution
    des hooks et du processus agent entre les snapshots.
    """
    before_hooks = capture_git_snapshot(
        repo_root,
        worktree_path=worktree_path,
        timestamp_label="before_hooks",
    )
    after_hooks = capture_git_snapshot(
        repo_root,
        worktree_path=worktree_path,
        timestamp_label="after_hooks",
    )
    after_process = capture_git_snapshot(
        repo_root,
        worktree_path=worktree_path,
        timestamp_label="after_process",
    )

    return GitSnapshotTriple(
        before_hooks=before_hooks,
        after_hooks=after_hooks,
        after_process=after_process,
    )


def capture_git_snapshot_triple_with_lifecycle(
    repo_root: Path,
    worktree_path: Path | None = None,
    hooks_phase: Callable[[], None] | None = None,
    agent_phase: Callable[[], None] | None = None,
) -> GitSnapshotTriple:
    """Orchestre les trois captures aux instants réels du cycle de tentative.

    Paramètres:
    - repo_root: racine du dépôt Git
    - worktree_path: chemin du worktree cible (optionnel)
    - hooks_phase: callable exécuté après before_hooks et avant after_hooks.
                   Simule l'exécution des hooks d'initialisation du runner.
    - agent_phase: callable exécuté après after_hooks et avant after_process.
                   Simule l'exécution du processus agent.

    Retourne un GitSnapshotTriple avec les trois snapshots capturés aux
    trois instants distincts du cycle réel. Les snapshots after_hooks et
    after_process capturent aussi les chemins affectés par les changements
    de HEAD (commits).
    """
    if worktree_path is None:
        worktree_path = repo_root

    before_hooks = capture_git_snapshot(
        repo_root,
        worktree_path=worktree_path,
        timestamp_label="before_hooks",
    )

    if hooks_phase is not None:
        hooks_phase()

    after_hooks = capture_git_snapshot(
        repo_root,
        worktree_path=worktree_path,
        timestamp_label="after_hooks",
        previous_head=before_hooks.head,
    )

    if agent_phase is not None:
        agent_phase()

    after_process = capture_git_snapshot(
        repo_root,
        worktree_path=worktree_path,
        timestamp_label="after_process",
        previous_head=after_hooks.head,
    )

    return GitSnapshotTriple(
        before_hooks=before_hooks,
        after_hooks=after_hooks,
        after_process=after_process,
    )


def categorize_agents_md_mutations(
    before_hooks: GitSnapshot,
    after_hooks: GitSnapshot,
    after_process: GitSnapshot,
) -> dict[str, Any]:
    """Cas spécial d'audit pour AGENTS.md.

    Compare explicitement avant/après hooks et avant/après processus
    pour identifier les mutations du bloc claude-mem.
    """
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)
    agents_md_attr = attributions.get("AGENTS.md")

    return {
        "path": "AGENTS.md",
        "before_hooks": {
            "dirty": "AGENTS.md" in before_hooks.tracked_dirty,
            "untracked": "AGENTS.md" in before_hooks.untracked,
        },
        "hook_mutation": agents_md_attr.hook_mutation if agents_md_attr else False,
        "agent_mutation": agents_md_attr.agent_mutation if agents_md_attr else False,
        "after_process": {
            "dirty": "AGENTS.md" in after_process.tracked_dirty,
            "untracked": "AGENTS.md" in after_process.untracked,
        },
    }


def capture_content_fingerprints(snapshot: GitSnapshot) -> ContentFingerprints:
    """Capture les empreintes de contenu d'un snapshot.

    AC-R22-3: Compare le contenu via empreintes déterministes par fichier,
    couvrant blob indexé, contenu worktree et fichiers non suivis.
    """
    # Organiser les hashes par catégorie
    if snapshot.file_hashes is None:
        return ContentFingerprints(timestamp_label=snapshot.timestamp_label)

    index_set = set(snapshot.index_changed)
    dirty_set = set(snapshot.tracked_dirty)
    untracked_set = set(snapshot.untracked)

    indexed_blob_hashes = {}
    worktree_content_hashes = {}
    untracked_file_hashes = {}

    # AC-R22-3: Utiliser les hashes indexés séparés si disponibles
    if snapshot.indexed_blob_hashes is not None:
        indexed_blob_hashes = dict(snapshot.indexed_blob_hashes)

    for path, hash_value in snapshot.file_hashes.items():
        # Un fichier peut être à la fois staged et dirty.
        # Dans ce cas, on doit capturer BOTH:
        # - indexed_blob_hashes[path] = hash du blob indexé
        # - worktree_content_hashes[path] = hash du contenu worktree
        # Ceci capture la distinction requise par R22-3.

        # Ajouter au hash indexé (fallback si pas disponible séparément)
        if path in index_set and path not in indexed_blob_hashes:
            # Fallback: utiliser le hash worktree si blob indexé non disponible
            indexed_blob_hashes[path] = hash_value

        # Ajouter au contenu worktree (NON-exclusif, contrairement au if/elif)
        if path in dirty_set:
            # Le contenu worktree du fichier dirty
            worktree_content_hashes[path] = hash_value

        # Ajouter au fichiers non suivis
        if path in untracked_set:
            # Le contenu du fichier non suivi
            untracked_file_hashes[path] = hash_value

    return ContentFingerprints(
        indexed_blob_hashes=indexed_blob_hashes,
        worktree_content_hashes=worktree_content_hashes,
        untracked_file_hashes=untracked_file_hashes,
        timestamp_label=snapshot.timestamp_label,
    )


def detect_content_changes(
    before: ContentFingerprints,
    after: ContentFingerprints,
) -> list[ModificationChange]:
    """Détecte les changements de contenu entre deux séries d'empreintes.

    AC-R22-3: Compare le contenu par catégorie (indexed, tracked_dirty, untracked).
    AC-R22-4: Détecte une nouvelle modification sur un fichier déjà modifié.
    """
    changes: list[ModificationChange] = []

    # AC-R22-3: Comparer par catégorie séparée pour préserver les distinctions
    # Identifier tous les chemins uniques à travers toutes les catégories
    all_paths_indexed = set(before.indexed_blob_hashes.keys()) | set(after.indexed_blob_hashes.keys())
    all_paths_dirty = set(before.worktree_content_hashes.keys()) | set(after.worktree_content_hashes.keys())
    all_paths_untracked = set(before.untracked_file_hashes.keys()) | set(after.untracked_file_hashes.keys())

    # Traiter indexed blobs
    for path in all_paths_indexed:
        before_hash = before.indexed_blob_hashes.get(path)
        after_hash = after.indexed_blob_hashes.get(path)
        hash_changed = before_hash is not None and after_hash is not None and before_hash != after_hash
        presence_changed = (before_hash is None) != (after_hash is None)

        if hash_changed or presence_changed:
            changes.append(
                ModificationChange(
                    path=path,
                    category="indexed",
                    before_hash=before_hash,
                    after_hash=after_hash,
                    hash_changed=hash_changed,
                    presence_changed=presence_changed,
                )
            )

    # Traiter worktree content (dirty tracked files)
    for path in all_paths_dirty:
        before_hash = before.worktree_content_hashes.get(path)
        after_hash = after.worktree_content_hashes.get(path)
        hash_changed = before_hash is not None and after_hash is not None and before_hash != after_hash
        presence_changed = (before_hash is None) != (after_hash is None)

        if hash_changed or presence_changed:
            changes.append(
                ModificationChange(
                    path=path,
                    category="tracked_dirty",
                    before_hash=before_hash,
                    after_hash=after_hash,
                    hash_changed=hash_changed,
                    presence_changed=presence_changed,
                )
            )

    # Traiter untracked files
    for path in all_paths_untracked:
        before_hash = before.untracked_file_hashes.get(path)
        after_hash = after.untracked_file_hashes.get(path)
        hash_changed = before_hash is not None and after_hash is not None and before_hash != after_hash
        presence_changed = (before_hash is None) != (after_hash is None)

        if hash_changed or presence_changed:
            changes.append(
                ModificationChange(
                    path=path,
                    category="untracked",
                    before_hash=before_hash,
                    after_hash=after_hash,
                    hash_changed=hash_changed,
                    presence_changed=presence_changed,
                )
            )

    return changes


def classify_modifications(
    snapshot: GitSnapshot,
    modified_paths: list[str],
    mutations: dict[str, MutationAttribution],
) -> list[ModificationClassification]:
    """Classifie les modifications selon le scope autorisé.

    AC-R11-3: Classe les modifications en autorisées, partielles ou hors scope.
    AC-R11-4: Les modifications autorisées sont conservées.

    Les modified_paths sont des scopes hiérarchiques (allowd_paths) qui peuvent être:
    - Des chemins exacts (ex: "file.py")
    - Des répertoires (ex: "src")

    Un chemin de fichier est autorisé s'il:
    - Est exact match avec un scope, OU
    - Est un enfant d'un scope répertoire (ex: "src/nested/file.py" est enfant de "src")
    """
    classifications: list[ModificationClassification] = []

    # Normaliser les allowed_paths (scopes hiérarchiques)
    try:
        normalized_allowed = [normalize_repo_relative_path(item) for item in modified_paths]
    except ValueError as exc:
        raise GitContextError(str(exc)) from exc

    all_dirty = set(snapshot.index_changed + snapshot.tracked_dirty + snapshot.untracked)

    for path in sorted(all_dirty):
        attribution = mutations.get(path)
        is_preexisting = attribution.before_hooks if attribution else False
        is_agent_mutation = attribution.agent_mutation if attribution else False

        # Vérifier si le chemin est autorisé via matching hiérarchique
        try:
            normalized_path = normalize_repo_relative_path(path)
        except ValueError:
            # Chemin invalide => pas autorisé
            is_allowed = False
        else:
            is_allowed = any(
                path_matches_allowed_scope(snapshot, normalized_path, allowed_scope)
                for allowed_scope in normalized_allowed
            )

        # Determine classification type based on scope and origin
        # preexisting: dirty before process start
        # allowed: modification (agent or otherwise) on an allowed path
        # out_of_scope: modification not in allowed paths
        # partial: preexisting + allowed (carries both states)
        if is_preexisting and is_allowed:
            classification_type: Literal["allowed", "partial", "out_of_scope", "preexisting"] = "partial"
        elif is_preexisting and not is_allowed:
            classification_type = "preexisting"
        elif is_allowed:
            classification_type = "allowed"
        else:
            classification_type = "out_of_scope"

        classifications.append(
            ModificationClassification(
                path=path,
                is_allowed=is_allowed,
                is_preexisting=is_preexisting,
                is_agent_mutation=is_agent_mutation,
                classification=classification_type,
            )
        )

    return classifications


def diagnose_reconciliation(
    before_hooks: GitSnapshot,
    after_process: GitSnapshot,
    modified_paths: list[str],
    mutations: dict[str, MutationAttribution] | None = None,
) -> ReconciliationDiagnostic:
    """Produit un diagnostic structuré pour la réconciliation.

    AC-R11-5: Diagnostic structuré précède toute reprise.
    AC-R11-12: Si l'attribution d'un changement est ambiguë, REQUEST_HUMAN est imposé.
    AC-R22-9: Produit des preuves vérifiables reliant avant/après, empreintes, classements.
    AC-R22-7: Les modifications autorisées cohérentes peuvent être reprises ; ambiguïté impose REQUEST_HUMAN.
    """
    if mutations is None:
        mutations = {}

    # Capturer les empreintes de contenu
    before_fingerprints = capture_content_fingerprints(before_hooks)
    after_fingerprints = capture_content_fingerprints(after_process)
    content_changes = detect_content_changes(before_fingerprints, after_fingerprints)

    # Classifier les modifications
    classifications = classify_modifications(after_process, modified_paths, mutations)

    preexisting_dirty = [c.path for c in classifications if c.is_preexisting]
    allowed = [c for c in classifications if c.classification == "allowed"]
    partial = [c for c in classifications if c.classification == "partial"]
    out_of_scope = [c for c in classifications if c.classification == "out_of_scope"]

    # AC-R11-12: Vérifier les origines ambiguës des mutations
    # AC-R22-7: Toute ambiguïté d'attribution, quel que soit le scope, impose REQUEST_HUMAN
    modified_paths_set = set(modified_paths)
    has_ambiguous_origin = False
    for path in set(c.path for c in classifications):
        mutation = mutations.get(path)
        if mutation is not None:
            # Si l'attribution est ambiguë, REQUEST_HUMAN est imposé
            # (AC-R11-12, AC-R22-7)
            if mutation.ambiguous_origin:
                has_ambiguous_origin = True
                break
            # Origines externes ou indéterminées => REQUEST_HUMAN
            # (AC-R22-7)
            if mutation.origin in ("external", "indeterminate"):
                has_ambiguous_origin = True
                break

    # Déterminer le verdict
    has_divergence = len(out_of_scope) > 0
    has_content_changes = len(content_changes) > 0
    # AC-R22-7: Utiliser la même sémantique de scope hiérarchique que classify_modifications()
    # pour déterminer si un changement de contenu est hors scope
    try:
        normalized_allowed = [normalize_repo_relative_path(item) for item in modified_paths]
    except ValueError:
        normalized_allowed = []

    has_ambiguity = False
    for ch in content_changes:
        if ch.hash_changed:
            try:
                normalized_path = normalize_repo_relative_path(ch.path)
            except ValueError:
                # Chemin invalide => ambigu
                has_ambiguity = True
                break

            # Vérifier si le chemin est dans un scope autorisé (matching hiérarchique)
            is_in_allowed_scope = any(
                path_matches_allowed_scope(after_process, normalized_path, allowed_scope)
                for allowed_scope in normalized_allowed
            )

            if not is_in_allowed_scope:
                has_ambiguity = True
                break

    # AC-R11-12: Appliquer la logique de verdict
    # AC-R22-7: Assouplir pour mutations agent_mutation prouvées hors scope
    # Une mutation hors scope prouvée comme agent_mutation n'est pas ambiguë,
    # même avec changement de contenu, si elle peut être restaurée en toute sécurité.

    # Vérifier si TOUS les changements hors scope sont prouvés agent_mutation
    all_out_of_scope_are_agent = all(
        mutations.get(oc.path, MutationAttribution(
            path=oc.path,
            before_hooks=False,
            hook_mutation=False,
            agent_mutation=False,
            external_mutation=False,
        )).agent_mutation
        for oc in out_of_scope
    )

    if has_ambiguous_origin:
        # Origines externes, indéterminées ou ambiguës => REQUEST_HUMAN
        verdict: Literal["safe_to_recover", "requires_review", "request_human"] = "request_human"
    elif has_ambiguity and not (has_divergence and all_out_of_scope_are_agent):
        # Changements de contenu sur des chemins non autorisés, sauf si tous
        # les out_of_scope sont prouvés agent_mutation => REQUEST_HUMAN
        verdict = "request_human"
    elif has_divergence or len(partial) > 0:
        # Divergence (changements out_of_scope) ou parcelles (partiellement autorisées)
        # => requires_review (pour validation/revue)
        verdict = "requires_review"
    else:
        verdict = "safe_to_recover"

    # Construire les preuves avec attribution
    evidence = {
        "preexisting_dirty_paths": preexisting_dirty,
        "content_changes": [
            {
                "path": ch.path,
                "category": ch.category,
                "before_hash": ch.before_hash,
                "after_hash": ch.after_hash,
                "hash_changed": ch.hash_changed,
                "presence_changed": ch.presence_changed,
            }
            for ch in content_changes
        ],
        "classification_summary": {
            "allowed_count": len(allowed),
            "partial_count": len(partial),
            "out_of_scope_count": len(out_of_scope),
        },
        "mutation_attributions": {
            path: {
                "origin": mutation.origin,
                "agent_mutation": mutation.agent_mutation,
                "external_mutation": mutation.external_mutation,
                "ambiguous_origin": mutation.ambiguous_origin,
            }
            for path, mutation in mutations.items()
        },
    }

    return ReconciliationDiagnostic(
        has_divergence=has_divergence,
        preexisting_dirty_paths=preexisting_dirty,
        allowed_changes=allowed,
        partial_changes=partial,
        out_of_scope_changes=out_of_scope,
        content_changes_detected=content_changes,
        verdict=verdict,
        evidence=evidence,
    )


@dataclass(frozen=True)
class GitReconstructionIncident:
    """Incident detected during runtime state reconstruction from Git."""
    code: str
    reason: str
    evidence: list[str]
    path_affected: str | None = None
    expected_value: str | None = None
    actual_value: str | None = None


def verify_branch_exists(repo_root: Path, branch: str) -> GitReconstructionIncident | None:
    """Verify that a branch exists in Git. AC-R2.2, AC-R2.3."""
    try:
        if not branch_exists(repo_root, branch):
            return GitReconstructionIncident(
                code="BRANCH_NOT_FOUND",
                reason=f"Branch {branch} does not exist",
                evidence=[f"git branch -r | grep {branch} returned nothing"],
            )
    except GitError as e:
        return GitReconstructionIncident(
            code="BRANCH_CHECK_FAILED",
            reason=f"Failed to check if branch exists: {e}",
            evidence=[str(e)],
        )
    return None


def verify_branch_head(repo_root: Path, branch: str, expected_commit: str) -> GitReconstructionIncident | None:
    """Verify that a branch points to the expected commit. AC-R2.2, AC-R2.3."""
    try:
        actual_head = branch_head(repo_root, branch)
        if actual_head != expected_commit:
            return GitReconstructionIncident(
                code="BRANCH_HEAD_DIVERGENCE",
                reason=f"Branch {branch} HEAD diverged",
                evidence=[
                    f"Expected: {expected_commit}",
                    f"Actual: {actual_head}",
                ],
                path_affected=branch,
                expected_value=expected_commit,
                actual_value=actual_head,
            )
    except GitError as e:
        return GitReconstructionIncident(
            code="BRANCH_HEAD_CHECK_FAILED",
            reason=f"Failed to check branch HEAD: {e}",
            evidence=[str(e)],
        )
    return None


def verify_worktree_state(
    repo_root: Path,
    worktree_path: Path,
    expected_branch: str | None = None,
    expected_head: str | None = None,
) -> list[GitReconstructionIncident]:
    """Verify worktree state against Git reality. AC-R2.2, AC-R2.3."""
    incidents: list[GitReconstructionIncident] = []

    # Check if worktree path exists
    if not worktree_path.exists():
        incidents.append(GitReconstructionIncident(
            code="WORKTREE_PATH_NOT_FOUND",
            reason=f"Worktree path does not exist: {worktree_path}",
            evidence=[f"Path.exists() = False"],
            path_affected=str(worktree_path),
        ))
        return incidents

    # Check if registered in git
    try:
        if not worktree_registered(repo_root, worktree_path):
            incidents.append(GitReconstructionIncident(
                code="WORKTREE_NOT_REGISTERED",
                reason=f"Worktree not registered in git: {worktree_path}",
                evidence=["git worktree list does not include this path"],
                path_affected=str(worktree_path),
            ))
            return incidents
    except GitError as e:
        incidents.append(GitReconstructionIncident(
            code="WORKTREE_CHECK_FAILED",
            reason=f"Failed to check worktree registration: {e}",
            evidence=[str(e)],
            path_affected=str(worktree_path),
        ))
        return incidents

    # Check current branch if expected
    if expected_branch:
        try:
            actual_branch = current_branch(repo_root, cwd=worktree_path)
            if actual_branch != expected_branch:
                incidents.append(GitReconstructionIncident(
                    code="WORKTREE_BRANCH_DIVERGENCE",
                    reason=f"Worktree branch diverged: {worktree_path}",
                    evidence=[
                        f"Expected branch: {expected_branch}",
                        f"Actual branch: {actual_branch}",
                    ],
                    path_affected=str(worktree_path),
                    expected_value=expected_branch,
                    actual_value=actual_branch,
                ))
        except GitError as e:
            incidents.append(GitReconstructionIncident(
                code="WORKTREE_BRANCH_CHECK_FAILED",
                reason=f"Failed to check worktree branch: {e}",
                evidence=[str(e)],
                path_affected=str(worktree_path),
            ))

    # Check current HEAD if expected
    if expected_head:
        try:
            actual_head = current_head(repo_root, cwd=worktree_path)
            if actual_head != expected_head:
                incidents.append(GitReconstructionIncident(
                    code="WORKTREE_HEAD_DIVERGENCE",
                    reason=f"Worktree HEAD diverged: {worktree_path}",
                    evidence=[
                        f"Expected HEAD: {expected_head}",
                        f"Actual HEAD: {actual_head}",
                    ],
                    path_affected=str(worktree_path),
                    expected_value=expected_head,
                    actual_value=actual_head,
                ))
        except GitError as e:
            incidents.append(GitReconstructionIncident(
                code="WORKTREE_HEAD_CHECK_FAILED",
                reason=f"Failed to check worktree HEAD: {e}",
                evidence=[str(e)],
                path_affected=str(worktree_path),
            ))

    return incidents
