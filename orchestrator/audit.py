from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import re

from orchestrator.models.product_audit import AuditBacklog
REQUIRED_OUTPUTS = (
    "product/FEATURE_MATRIX.md",
    "product/GAP_ANALYSIS.md",
    "product/USER_JOURNEYS.md",
    "product/ALPHA_ROADMAP.md",
    "tasks/backlog.json",
    "reports/product/PRODUCT_AUDIT_REPORT.md",
)

AUDIT_STATUSES = {
    "completed": "AUDIT_COMPLETED",
    "codex_failed": "AUDIT_FAILED_CODEX",
    "timeout": "AUDIT_FAILED_TIMEOUT",
    "missing_output": "AUDIT_FAILED_MISSING_OUTPUT",
    "invalid_backlog": "AUDIT_FAILED_INVALID_BACKLOG",
    "empty_backlog": "AUDIT_FAILED_EMPTY_BACKLOG",
    "unauthorized_changes": "AUDIT_FAILED_UNAUTHORIZED_CHANGES",
    "already_exists": "AUDIT_ALREADY_EXISTS",
    "dry_run": "AUDIT_DRY_RUN",
}


class AuditError(Exception):
    def __init__(self, status: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.details = details or {}


@dataclass(slots=True)
class SourceInventory:
    repo_root: Path
    categories: dict[str, list[str]]

    def summary(self) -> dict[str, int]:
        return {name: len(paths) for name, paths in self.categories.items()}

    def to_prompt_block(self) -> str:
        lines = []
        for name, paths in self.categories.items():
            lines.append(f"## {name}")
            for path in paths:
                lines.append(f"- {path}")
            if not paths:
                lines.append("- [aucun fichier detecte]")
            lines.append("")
        return "\n".join(lines).strip()


def detect_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise AuditError("AUDIT_FAILED_CODEX", "Unable to detect repository root.")


def resolve_output_root(repo_root: Path, output_root: Path | None) -> Path:
    resolved = (output_root or repo_root).resolve()
    if resolved != repo_root and repo_root not in resolved.parents:
        raise AuditError(
            "AUDIT_FAILED_CODEX",
            "Output root must be the repository root or one of its subdirectories.",
            details={"output_root": str(resolved)},
        )
    return resolved


def required_output_paths(output_root: Path) -> dict[str, Path]:
    return {relative: output_root / relative for relative in REQUIRED_OUTPUTS}


def collect_source_inventory(repo_root: Path) -> SourceInventory:
    categories = {
        "specifications": _collect_existing(
            repo_root,
            [
                "SPEC.md",
                "ROADMAP.md",
                "AGENTS.md",
                "agents/STATUS.md",
                "agents/QUEUE.md",
            ],
        ),
        "frontend": _sorted_glob(repo_root, "src/**/*"),
        "backend": _sorted_glob(repo_root, "src-tauri/src/**/*"),
        "migrations": _sorted_glob(repo_root, "src-tauri/migrations/**/*"),
        "rust_tests": _sorted_glob(repo_root, "src-tauri/tests/**/*"),
        "frontend_tests": _sorted_glob(repo_root, "src/__tests__/**/*"),
        "playwright_tests": _sorted_glob(repo_root, "tests/e2e/**/*"),
        "reports": _sorted_glob(repo_root, "reports/**/*"),
        "packaging": _collect_existing(
            repo_root,
            [
                "package.json",
                "Cargo.toml",
                "src-tauri/Cargo.toml",
                "src-tauri/tauri.conf.json",
                "playwright.config.ts",
                "docs/PACKAGING_WINDOWS.md",
                "docs/PACKAGING_LINUX_APPIMAGE.md",
                "docs/PACKAGING_LINUX_DEB.md",
                ".github/workflows/release-v0.1-artifacts.yml",
            ],
        ),
        "appimage_findings": _collect_appimage_findings(repo_root),
    }
    return SourceInventory(repo_root=repo_root, categories=categories)


def build_audit_prompt(template_text: str, inventory: SourceInventory, output_root: Path) -> str:
    outputs_block = "\n".join(f"- {path}" for path in REQUIRED_OUTPUTS)
    return (
        f"{template_text.strip()}\n\n"
        "Contraintes operatoires obligatoires:\n"
        "- Lire reellement les sources listees ci-dessous avant de conclure.\n"
        "- Tu peux lire tout le depot.\n"
        "- Tu ne dois creer ou modifier que les livrables d'audit suivants:\n"
        f"{outputs_block}\n"
        "- Ne modifie aucun fichier sous src/ ou src-tauri/.\n"
        "- Les anciens verdicts MVP, QA ou release sont des indices, pas des preuves suffisantes.\n"
        "- La regle centrale est: une fonctionnalite n'est presente que si un agent de mairie peut reellement l'utiliser dans l'application packagee, sans terminal.\n"
        "- Le backlog doit etre un JSON valide conforme au schema demande.\n"
        "- Chaque tache doit etre atomique et verifiable par un utilisateur.\n"
        f"- Ecris les livrables sous la racine de sortie: {output_root}.\n\n"
        "Sources detectees a auditer:\n"
        f"{inventory.to_prompt_block()}\n"
    )


def archive_existing_outputs(output_root: Path, archive_root: Path, required_outputs: dict[str, Path]) -> Path | None:
    existing = [path for path in required_outputs.values() if path.exists() and path.stat().st_size > 0]
    if not existing:
        return None
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination_root = archive_root / timestamp
    for path in existing:
        destination = destination_root / path.relative_to(output_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    return destination_root


def ensure_outputs_absent(required_outputs: dict[str, Path]) -> None:
    existing = [str(path) for path in required_outputs.values() if path.exists() and path.stat().st_size > 0]
    if existing:
        raise AuditError(
            "AUDIT_ALREADY_EXISTS",
            "Audit outputs already exist. Use --force to archive and regenerate them.",
            details={"existing_outputs": existing},
        )


def validate_required_outputs(required_outputs: dict[str, Path]) -> None:
    missing = [relative for relative, path in required_outputs.items() if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise AuditError(
            "AUDIT_FAILED_MISSING_OUTPUT",
            "Codex did not produce all required audit outputs.",
            details={"missing_outputs": missing},
        )


def validate_backlog_file(path: Path) -> AuditBacklog:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditError(
            "AUDIT_FAILED_INVALID_BACKLOG",
            "Backlog JSON is invalid.",
            details={"error": str(exc), "path": str(path)},
        ) from exc
    try:
        backlog = AuditBacklog.model_validate(payload)
    except ValueError as exc:
        message = str(exc)
        status = "AUDIT_FAILED_EMPTY_BACKLOG" if "at least one task" in message.lower() else "AUDIT_FAILED_INVALID_BACKLOG"
        raise AuditError(status, "Backlog validation failed.", details={"error": message, "path": str(path)}) from exc
    if not backlog.tasks:
        raise AuditError("AUDIT_FAILED_EMPTY_BACKLOG", "Backlog contains no tasks.", details={"path": str(path)})
    return backlog


def snapshot_git_status(repo_root: Path) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--short"],
        check=True,
        text=True,
        capture_output=True,
    )
    snapshot: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        snapshot[line[3:]] = line[:2]
    return snapshot


def detect_unauthorized_changes(before: dict[str, str], after: dict[str, str]) -> list[str]:
    unauthorized: list[str] = []
    for path, status in after.items():
        if before.get(path) == status:
            continue
        normalized = path.replace("\\", "/")
        if normalized == "tasks/backlog.json":
            continue
        if any(normalized.startswith(prefix) for prefix in ("product/", "reports/product/")):
            continue
        unauthorized.append(normalized)
    return sorted(unauthorized)


def parse_critical_gap_count(backlog: AuditBacklog) -> int:
    return sum(1 for task in backlog.tasks if task.priority == "critical")


def parse_domain_count(backlog: AuditBacklog) -> int:
    return len({task.domain for task in backlog.tasks})


def _collect_existing(repo_root: Path, relative_paths: list[str]) -> list[str]:
    return [relative for relative in relative_paths if (repo_root / relative).exists()]


def _sorted_glob(repo_root: Path, pattern: str) -> list[str]:
    return sorted(
        str(path.relative_to(repo_root))
        for path in repo_root.glob(pattern)
        if path.is_file()
    )


def _search_paths(repo_root: Path, pattern: str) -> list[str]:
    regex = re.compile(pattern)
    matches: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        relative = str(path.relative_to(repo_root))
        if regex.search(relative):
            matches.append(relative)
            continue
        if path.suffix.lower() in {".md", ".txt", ".json", ".yml", ".yaml", ".toml"}:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if regex.search(content):
                matches.append(relative)
    return sorted(set(matches))


def _collect_appimage_findings(repo_root: Path) -> list[str]:
    explicit = _collect_existing(
        repo_root,
        [
            "docs/PACKAGING_LINUX_APPIMAGE.md",
            "reports/dev/MVP-22.md",
            "reports/release/pilot_v0.1_artifacts_report.md",
            "reports/release/pilot_v0.1_release_status_final.md",
            "reports/release/pilot_v0.1_release_validation.md",
            "reports/release/pilot_v0.1_workflow_status.md",
            "reports/release/pilot_v0.1_workflow_diagnosis.md",
            "reports/qa/mvp27_final_release_audit.md",
        ],
    )
    searched_roots = ["reports", "docs", "agents", "ROADMAP.md", "SPEC.md", "src-tauri/tauri.conf.json"]
    matches: list[str] = []
    for entry in searched_roots:
        path = repo_root / entry
        if not path.exists():
            continue
        if path.is_file():
            candidates = [path]
        else:
            candidates = [candidate for candidate in path.rglob("*") if candidate.is_file()]
        for candidate in candidates:
            relative = str(candidate.relative_to(repo_root))
            if relative in explicit:
                matches.append(relative)
                continue
            if candidate.suffix.lower() not in {".md", ".txt", ".json", ".yml", ".yaml", ".toml"}:
                continue
            content = candidate.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"appimage|AppImage", content) or re.search(r"appimage|AppImage", relative):
                matches.append(relative)
    return sorted(set(explicit + matches))
