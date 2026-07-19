from __future__ import annotations

from pathlib import Path


KNOWN_GENERATED_ARTIFACTS = (
    "playwright-report",
    "test-results",
    "dist",
    "coverage",
    "target",
    "htmlcov",
    ".pytest_cache",
    "__pycache__",
)

DEPENDENCY_MANIFEST_PATHS = {
    "package.json",
    "package-lock.json",
    "Cargo.lock",
    "src-tauri/Cargo.toml",
}

INSTALL_COMMAND_MARKERS = (
    "npm install",
    "npm i ",
    "pnpm add",
    "yarn add",
    "cargo add",
    "pip install",
)

WIDE_VALIDATION_COMMANDS = {
    "npm run test",
    "npm test",
    "pnpm test",
    "yarn test",
    "cargo test",
    "pytest",
}


def is_known_generated_artifact(path: str) -> bool:
    normalized = path.strip("/").replace("\\", "/")
    if not normalized:
        return False
    first = normalized.split("/", 1)[0]
    return first in KNOWN_GENERATED_ARTIFACTS


def filter_generated_artifacts(
    paths: list[str],
    *,
    is_tracked: callable,
) -> list[str]:
    filtered: list[str] = []
    for path in paths:
        if is_known_generated_artifact(path) and not is_tracked(path):
            continue
        filtered.append(path)
    return filtered


def is_dependency_manifest(path: str) -> bool:
    normalized = path.strip("/").replace("\\", "/")
    return normalized in DEPENDENCY_MANIFEST_PATHS


def command_installs_dependencies(command: str) -> bool:
    normalized = f" {command.casefold()} "
    return any(marker in normalized for marker in INSTALL_COMMAND_MARKERS)


def command_is_manifestly_wide(command: str) -> bool:
    normalized = command.strip().casefold()
    if normalized in WIDE_VALIDATION_COMMANDS:
        return True
    return normalized.startswith("npm run test ") and "--" not in normalized


def infer_targeted_test_paths(allowed_paths: list[str]) -> list[str]:
    targeted: list[str] = []
    for raw_path in allowed_paths:
        path = Path(raw_path)
        name = path.name.casefold()
        if ".test." in name or ".spec." in name:
            targeted.append(raw_path)
    return sorted(set(targeted))
