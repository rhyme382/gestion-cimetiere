from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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


@dataclass(frozen=True)
class GitSnapshotTriple:
    """Trois snapshots pour audit de mutations (avant hooks, après hooks, après processus)."""
    before_hooks: GitSnapshot
    after_hooks: GitSnapshot
    after_process: GitSnapshot


@dataclass(frozen=True)
class MutationAttribution:
    """Attribution d'une mutation à sa source (hook, agent, préexistant)."""
    path: str
    before_hooks: bool
    hook_mutation: bool
    agent_mutation: bool
    external_mutation: bool


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
) -> GitSnapshot:
    """Capture une vue détaillée de l'état Git à un moment donné.

    Capture toujours les hashes de fichiers pour détecter les mutations
    de contenu même sur les fichiers déjà dirty (prérequis pour audit
    fiable des mutations de hook vs agent sur état préexistant).
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
        )
    except GitError as exc:
        raise GitContextError(f"Impossible de capturer l'état Git : {exc}") from exc


def analyze_mutations(
    before_hooks: GitSnapshot,
    after_hooks: GitSnapshot,
    after_process: GitSnapshot,
) -> dict[str, MutationAttribution]:
    """Analyse les mutations et les attribue à leur source.

    Distingue:
    - mutations préexistantes (avant hooks)
    - mutations de hook (entre avant_hooks et after_hooks)
    - mutations d'agent (entre after_hooks et after_process)
    - mutations externes (modifications impossibles à attribuer au hook ou à l'agent)

    Utilise les hashes de fichiers pour détecter les changements
    même quand le statut dirty est identique (cas critique pour
    fichiers préexistants modifiés par hook puis agent).

    La détection des mutations externes se base sur:
    - Les changements de HEAD qui suggèrent un commit externe
    """
    attributions: dict[str, MutationAttribution] = {}
    head_changed = before_hooks.head != after_process.head

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

        hook_mutation = (not before_hooks_dirty and after_hooks_dirty) or hook_content_changed
        agent_mutation = (not after_hooks_dirty and after_process_dirty) or agent_content_changed

        external_mutation = False
        if head_changed:
            if (after_hooks_dirty and not after_process_dirty) or (not after_hooks_dirty and after_process_dirty):
                external_mutation = True

        if before_hooks_dirty or hook_mutation or agent_mutation or external_mutation:
            attributions[path] = MutationAttribution(
                path=path,
                before_hooks=before_hooks_dirty,
                hook_mutation=hook_mutation,
                agent_mutation=agent_mutation,
                external_mutation=external_mutation,
            )

    return attributions


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
    trois instants distincts du cycle réel.
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
    )

    if agent_phase is not None:
        agent_phase()

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
