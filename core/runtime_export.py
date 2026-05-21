from __future__ import annotations

import shutil
import struct
from pathlib import Path

from models.asset_job import AssetJob


RUNTIME_SUFFIXES = {".json", ".skel"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def collect_runtime_files(export_dir: Path, target_dir: Path, preferred_suffix: str) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []

    preferred = [path for path in export_dir.rglob("*") if path.is_file() and path.suffix.lower() == preferred_suffix]
    candidates = preferred or [path for path in export_dir.rglob("*") if path.is_file() and path.suffix.lower() in RUNTIME_SUFFIXES]

    for path in candidates:
        target_path = target_dir / path.name
        shutil.copy2(path, target_path)
        copied.append(target_path)

    return copied


def first_runtime_file(export_dir: Path, suffix: str) -> Path | None:
    for path in export_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() == suffix:
            return path
    return None


def build_unity_runtime_package(job: AssetJob, target_dir: Path, packed_atlas_dir: Path) -> list[Path]:
    if job.export_dir is None:
        raise RuntimeError("export folder is missing")

    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []

    skeleton_source = _select_skeleton(job)
    skeleton_target = _unity_skeleton_target(job, skeleton_source, target_dir)
    shutil.copy2(skeleton_source, skeleton_target)
    copied.append(skeleton_target)

    atlas_source = _select_atlas(packed_atlas_dir)
    atlas_target = target_dir / f"{job.name}.atlas.txt"
    shutil.copy2(atlas_source, atlas_target)
    copied.append(atlas_target)

    for image in _packed_atlas_images(packed_atlas_dir):
        image_target = target_dir / image.name
        shutil.copy2(image, image_target)
        copied.append(image_target)

    return copied


def _select_skeleton(job: AssetJob) -> Path:
    if job.export_dir is None:
        raise RuntimeError("export folder is missing")

    preferred_suffix = ".json" if _original_was_json(job) else ".skel"
    skeleton = first_runtime_file(job.export_dir, preferred_suffix)
    if skeleton is None:
        skeleton = first_runtime_file(job.export_dir, ".json" if preferred_suffix == ".skel" else ".skel")
    if skeleton is None:
        raise RuntimeError("no exported skeleton file was found")
    return skeleton


def _unity_skeleton_target(job: AssetJob, skeleton_source: Path, target_dir: Path) -> Path:
    if _original_was_json(job):
        return target_dir / f"{job.name}.json"
    return target_dir / f"{job.name}.skel.bytes"


def _original_was_json(job: AssetJob) -> bool:
    return job.normalized_skeleton_path is not None and job.normalized_skeleton_path.suffix.lower() == ".json"


def _atlas_images(job: AssetJob) -> list[Path]:
    if job.source_dir is None:
        return []
    return sorted(
        path
        for path in job.source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def _select_atlas(packed_atlas_dir: Path) -> Path:
    atlases = sorted(path for path in packed_atlas_dir.iterdir() if path.is_file() and path.suffix.lower() == ".atlas")
    if not atlases:
        raise RuntimeError("packed atlas file was not found")
    return atlases[0]


def _packed_atlas_images(packed_atlas_dir: Path) -> list[Path]:
    images = sorted(
        path
        for path in packed_atlas_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        raise RuntimeError("packed atlas image file was not found")
    return images


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return width, height
