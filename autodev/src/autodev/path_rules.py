from __future__ import annotations

from pathlib import Path


def normalize_repo_relative_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        raise ValueError(f"Chemin absolu interdit : {raw_path}")
    if any(part == ".." for part in path.parts):
        raise ValueError(f"Chemin avec '..' interdit : {raw_path}")

    normalized_parts = [part for part in path.parts if part not in ("", ".")]
    if not normalized_parts:
        raise ValueError(f"Chemin relatif invalide : {raw_path}")

    return Path(*normalized_parts)
