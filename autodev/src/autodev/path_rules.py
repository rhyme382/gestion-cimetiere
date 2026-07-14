from __future__ import annotations

from pathlib import Path, PurePosixPath


def normalize_repo_relative_path_text(raw_path: str) -> str:
    value = raw_path.replace("\\", "/")
    if value.startswith("./"):
        value = value[2:]

    path = PurePosixPath(value)
    if path.is_absolute():
        raise ValueError(f"Chemin absolu interdit : {raw_path}")
    if any(part == ".." for part in path.parts):
        raise ValueError(f"Chemin avec '..' interdit : {raw_path}")

    normalized_parts = [part for part in path.parts if part not in ("", ".")]
    if not normalized_parts:
        raise ValueError(f"Chemin relatif invalide : {raw_path}")

    return PurePosixPath(*normalized_parts).as_posix()


def normalize_repo_relative_path(raw_path: str) -> Path:
    normalized = normalize_repo_relative_path_text(raw_path)
    path = PurePosixPath(normalized)
    if not path.parts:
        raise ValueError(f"Chemin relatif invalide : {raw_path}")
    return Path(*path.parts)
