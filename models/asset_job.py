from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AssetJob:
    name: str
    output_name: str | None = None
    skeleton_path: Path | None = None
    atlas_path: Path | None = None
    image_paths: list[Path] = field(default_factory=list)
    source_dir: Path | None = None
    normalized_skeleton_path: Path | None = None
    normalized_atlas_path: Path | None = None
    detected_spine_version: str | None = None
    old_project_path: Path | None = None
    new_project_path: Path | None = None
    export_dir: Path | None = None
    unity_runtime_dir: Path | None = None
    status: str = "PENDING"
    message: str = ""

    @property
    def has_required_files(self) -> bool:
        return self.skeleton_path is not None and self.atlas_path is not None and bool(self.image_paths)

    @property
    def folder_name(self) -> str:
        return self.output_name or self.name

    def missing_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.skeleton_path is None:
            reasons.append("missing skeleton (.json, .skel, or .skel.bytes)")
        if self.atlas_path is None:
            reasons.append("missing atlas (.atlas or .atlas.txt)")
        if not self.image_paths:
            reasons.append("missing atlas image files")
        return reasons
