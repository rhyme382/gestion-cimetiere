from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from autodev.git_tools import (
    GitError,
    branch_head,
    changed_paths_between,
    compute_file_hashes,
    count_tracked_commits_between,
    current_branch,
    current_head,
    diff_patch_between,
    get_index_changed_paths,
    get_tracked_dirty_paths,
    get_untracked_paths,
    git_status_with_branch,
    name_status_between,
)
from autodev.planner import PlanningError, load_json


class GitContextError(RuntimeError):
    """État Git de tâche invalide ou incomplet."""


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
    # Chemins affectés par changement de HEAD (commits entre deux HEAD)
    paths_from_head_change: list[str] | None = None


@dataclass(frozen=True)
class GitSnapshotTriple:
    """Trois snapshots pour audit de mutations (avant hooks, après hooks, après processus)."""
    before_hooks: GitSnapshot
    after_hooks: GitSnapshot
    after_process: GitSnapshot


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
