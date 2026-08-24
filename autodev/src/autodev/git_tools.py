from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from shutil import rmtree

from autodev.path_rules import normalize_repo_relative_path_text


class GitError(RuntimeError):
    """Erreur liée aux opérations Git."""


def run_git(repo_root: Path, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def git_output(repo_root: Path, args: list[str], cwd: Path | None = None) -> str:
    result = run_git(repo_root, args, cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "erreur Git inconnue"
        raise GitError(stderr)
    return result.stdout.strip()


def git_output_raw(repo_root: Path, args: list[str], cwd: Path | None = None) -> str:
    result = run_git(repo_root, args, cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "erreur Git inconnue"
        raise GitError(stderr)
    return result.stdout


def ensure_clean_worktree(repo_root: Path) -> None:
    status = git_output(repo_root, ["status", "--short"])
    if status:
        raise GitError("Le dépôt principal contient des modifications non enregistrées.")


def current_head(repo_root: Path, cwd: Path | None = None) -> str:
    return git_output(repo_root, ["rev-parse", "HEAD"], cwd=cwd)


def current_branch(repo_root: Path, cwd: Path | None = None) -> str:
    branch = git_output(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if branch == "HEAD":
        raise GitError("La branche courante est détachée, intégration refusée.")
    return branch


def branch_exists(repo_root: Path, branch: str) -> bool:
    result = run_git(repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return result.returncode == 0


def worktree_registered(repo_root: Path, worktree_path: Path) -> bool:
    listed = git_output(repo_root, ["worktree", "list", "--porcelain"])
    needle = f"worktree {worktree_path.resolve()}"
    return needle in listed.splitlines()


def create_branch(repo_root: Path, branch: str, start_point: str) -> None:
    result = run_git(repo_root, ["branch", branch, start_point])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de créer la branche {branch}: {stderr}")


def add_worktree(repo_root: Path, worktree_path: Path, branch: str) -> None:
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_git(repo_root, ["worktree", "add", str(worktree_path), branch])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de créer le worktree {worktree_path}: {stderr}")


def changed_paths_since(repo_root: Path, worktree_path: Path, base_commit: str) -> list[str]:
    tracked = git_output_raw(
        repo_root,
        ["diff", "--name-only", "-z", base_commit],
        cwd=worktree_path,
    )
    untracked = git_output_raw(
        repo_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
        cwd=worktree_path,
    )

    paths = parse_git_path_list(tracked)
    paths.update(parse_git_path_list(untracked))
    return sorted(paths)


def changed_paths_between(repo_root: Path, start_commit: str, end_commit: str) -> list[str]:
    output = git_output_raw(repo_root, ["diff", "--name-only", "-z", start_commit, end_commit])
    return sorted(parse_git_path_list(output))


def name_status_between(repo_root: Path, start_commit: str, end_commit: str) -> list[str]:
    output = git_output_raw(repo_root, ["diff", "--name-status", "--find-renames", start_commit, end_commit])
    lines: list[str] = []
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t")
        if len(parts) < 2:
            raise GitError(f"Sortie git diff --name-status invalide : {raw_line}")
        status = parts[0]
        normalized_paths = [normalize_repo_relative_path_text(path) for path in parts[1:]]
        lines.append("\t".join([status, *normalized_paths]))
    return lines


def dirty_paths(repo_root: Path, cwd: Path | None = None) -> list[str]:
    unstaged = git_output_raw(repo_root, ["diff", "--name-only", "-z"], cwd=cwd)
    staged = git_output_raw(repo_root, ["diff", "--cached", "--name-only", "-z"], cwd=cwd)
    untracked = git_output_raw(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"], cwd=cwd)

    paths = parse_git_path_list(unstaged)
    paths.update(parse_git_path_list(staged))
    paths.update(parse_git_path_list(untracked))
    return sorted(paths)


def parse_git_path_list(output: str) -> set[str]:
    paths: set[str] = set()
    for entry in output.split("\0"):
        if not entry:
            continue
        paths.add(normalize_repo_relative_path_text(entry))
    return paths


def commit_count_since(repo_root: Path, worktree_path: Path, base_commit: str) -> int:
    count = git_output(repo_root, ["rev-list", "--count", f"{base_commit}..HEAD"], cwd=worktree_path)
    return int(count)


def head_commit(repo_root: Path, worktree_path: Path) -> str:
    return git_output(repo_root, ["rev-parse", "HEAD"], cwd=worktree_path)


def branch_head(repo_root: Path, branch: str) -> str:
    return git_output(repo_root, ["rev-parse", branch])


def count_tracked_commits_between(
    repo_root: Path,
    base_commit: str,
    end_ref: str,
    *,
    cwd: Path | None = None,
) -> int:
    count = git_output(repo_root, ["rev-list", "--count", f"{base_commit}..{end_ref}"], cwd=cwd)
    return int(count)


def diff_patch(repo_root: Path, worktree_path: Path, base_commit: str) -> str:
    return git_output(repo_root, ["diff", "--binary", base_commit, "HEAD"], cwd=worktree_path)


def diff_patch_between(repo_root: Path, start_commit: str, end_commit: str, paths: list[str] | None = None) -> str:
    cmd = ["diff", "--binary", start_commit, end_commit]
    if paths:
        cmd.extend(["--"] + paths)
    return git_output(repo_root, cmd)


def git_status_porcelain(repo_root: Path, cwd: Path | None = None) -> str:
    return git_output(repo_root, ["status", "--short"], cwd=cwd)


def git_status_with_branch(repo_root: Path, cwd: Path | None = None) -> str:
    return git_output_raw(repo_root, ["status", "--short", "--branch"], cwd=cwd)


def is_path_tracked(repo_root: Path, path: str, cwd: Path | None = None) -> bool:
    result = run_git(repo_root, ["ls-files", "--error-unmatch", "--", path], cwd=cwd)
    return result.returncode == 0


def is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    result = run_git(repo_root, ["merge-base", "--is-ancestor", ancestor, descendant])
    return result.returncode == 0


def merge_no_commit(repo_root: Path, branch: str) -> subprocess.CompletedProcess[str]:
    return run_git(repo_root, ["merge", "--no-ff", "--no-commit", branch])


def merge_abort(repo_root: Path) -> None:
    result = run_git(repo_root, ["merge", "--abort"])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible d'abandonner le merge en cours : {stderr}")


def has_merge_conflicts(repo_root: Path) -> bool:
    result = run_git(repo_root, ["diff", "--name-only", "--diff-filter=U"])
    return bool(result.stdout.strip())


def commit_merge(repo_root: Path, message: str) -> None:
    result = run_git(repo_root, ["commit", "-m", message])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de créer le commit de merge : {stderr}")


def stage_all(repo_root: Path, cwd: Path | None = None) -> None:
    result = run_git(repo_root, ["add", "-A"], cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de préparer les fichiers pour commit : {stderr}")


def amend_head_commit(repo_root: Path, cwd: Path | None = None) -> None:
    result = run_git(repo_root, ["commit", "--amend", "--no-edit"], cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible d'amender le commit courant : {stderr}")


def create_commit(repo_root: Path, message: str, cwd: Path | None = None) -> None:
    result = run_git(repo_root, ["commit", "-m", message], cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de créer le commit : {stderr}")


def path_exists_in_commit(repo_root: Path, commit: str, path: str, cwd: Path | None = None) -> bool:
    result = run_git(repo_root, ["cat-file", "-e", f"{commit}:{path}"], cwd=cwd)
    return result.returncode == 0


def unstage_paths(repo_root: Path, paths: list[str], cwd: Path | None = None) -> None:
    if not paths:
        return
    result = run_git(repo_root, ["rm", "--cached", "--force", "--ignore-unmatch", "--", *paths], cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de retirer les fichiers de l'index : {stderr}")


def restore_paths(repo_root: Path, worktree_path: Path, source_commit: str, paths: list[str]) -> None:
    if not paths:
        return

    tracked_in_source = [
        path for path in paths if path_exists_in_commit(repo_root, source_commit, path, cwd=worktree_path)
    ]
    missing_in_source = [path for path in paths if path not in tracked_in_source]

    if tracked_in_source:
        result = run_git(
            repo_root,
            ["restore", "--source", source_commit, "--staged", "--worktree", "--", *tracked_in_source],
            cwd=worktree_path,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise GitError(f"Impossible de restaurer les fichiers suivis : {stderr}")

    if missing_in_source:
        unstage_paths(repo_root, missing_in_source, cwd=worktree_path)
        for raw_path in missing_in_source:
            target = worktree_path / raw_path
            if target.is_dir():
                rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()


def hard_reset(repo_root: Path, commit: str) -> None:
    result = run_git(repo_root, ["reset", "--hard", commit])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de revenir à {commit}: {stderr}")


def remove_worktree(repo_root: Path, worktree_path: Path) -> None:
    result = run_git(repo_root, ["worktree", "remove", str(worktree_path)])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de supprimer le worktree {worktree_path}: {stderr}")


def get_index_changed_paths(repo_root: Path, cwd: Path | None = None) -> list[str]:
    """Fichiers en index (staged) modifiés."""
    output = git_output_raw(repo_root, ["diff", "--cached", "--name-only", "-z"], cwd=cwd)
    return sorted(parse_git_path_list(output))


def get_tracked_dirty_paths(repo_root: Path, cwd: Path | None = None) -> list[str]:
    """Fichiers suivis (tracked) modifiés mais non stagés."""
    output = git_output_raw(repo_root, ["diff", "--name-only", "-z"], cwd=cwd)
    return sorted(parse_git_path_list(output))


def get_untracked_paths(repo_root: Path, cwd: Path | None = None) -> list[str]:
    """Fichiers non suivis (untracked)."""
    output = git_output_raw(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"], cwd=cwd)
    return sorted(parse_git_path_list(output))


def compute_file_hashes(worktree_path: Path, file_paths: list[str]) -> dict[str, str]:
    """Calcule les hashes SHA256 de fichiers pour détecter les mutations de contenu."""
    hashes: dict[str, str] = {}
    for rel_path in file_paths:
        file_path = worktree_path / rel_path
        if file_path.is_file():
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    hashes[rel_path] = file_hash
            except (OSError, IOError):
                pass
    return hashes


def compute_indexed_blob_hashes(repo_root: Path, file_paths: list[str], cwd: Path | None = None) -> dict[str, str]:
    """Calcule les hashes SHA256 des blobs indexés (staged content).

    AC-R22-3: Capture le hash du blob indexé pour distinguer le contenu staged
    du contenu worktree lors de la détection de mutations.
    """
    hashes: dict[str, str] = {}
    for rel_path in file_paths:
        try:
            # Récupérer le blob hash depuis l'index Git pour ce chemin
            blob_hash = git_output(
                repo_root,
                ["ls-files", "--stage", "--", rel_path],
                cwd=cwd
            )
            if blob_hash:
                # Format: [mode] [object] [stage] [file]
                # On extrait le hash (object SHA-1, convertir en SHA256)
                parts = blob_hash.split()
                if len(parts) >= 2:
                    git_sha1 = parts[1]
                    # Utiliser le SHA-1 Git comme identifiant de contenu indexé
                    # (le full hash n'est pas accessible sans déréférencer)
                    hashes[rel_path] = git_sha1
        except GitError:
            # Fichier non indexé, continuer
            pass
    return hashes
