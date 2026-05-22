from __future__ import annotations

import json
import shutil
from pathlib import Path


def copy_images_for_project(unpacked_images_dir: Path, project_dir: Path, images_path: str = "images") -> Path:
    target_dir = resolve_project_images_dir(project_dir, images_path)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(unpacked_images_dir, target_dir)
    return target_dir


def resolve_project_images_dir(project_dir: Path, images_path: str) -> Path:
    clean_path = images_path.replace("\\", "/").strip() or "images"
    candidate = Path(clean_path)
    if candidate.is_absolute():
        return candidate
    return project_dir / clean_path


def read_json_images_path(json_path: Path) -> str | None:
    if json_path.suffix.lower() != ".json":
        return None
    data = json.loads(json_path.read_text(encoding="utf-8"))
    skeleton = data.get("skeleton", {})
    if not isinstance(skeleton, dict):
        return None
    value = skeleton.get("images")
    return str(value) if value else None


def patch_json_images_path(json_path: Path, images_path: str) -> bool:
    if json_path.suffix.lower() != ".json":
        return False

    data = json.loads(json_path.read_text(encoding="utf-8"))
    skeleton = data.setdefault("skeleton", {})
    if not isinstance(skeleton, dict):
        return False
    skeleton["images"] = images_path.replace("\\", "/").rstrip("/") + "/"
    json_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return True


def write_square_pack_settings(images_dir: Path) -> Path:
    settings_path = images_dir / "pack.json"
    settings = {
        "stripWhitespaceX": True,
        "stripWhitespaceY": True,
        "rotation": True,
        "alias": True,
        "ignoreBlankImages": False,
        "alphaThreshold": 3,
        "minWidth": 16,
        "minHeight": 16,
        "maxWidth": 4096,
        "maxHeight": 4096,
        "pot": False,
        "multipleOfFour": True,
        "square": True,
        "outputFormat": "png",
        "premultiplyAlpha": True,
        "bleed": True,
        "bleedIterations": 2,
        "paddingX": 2,
        "paddingY": 2,
        "edgePadding": True,
        "duplicatePadding": True,
        "atlasExtension": ".atlas",
        "combineSubdirectories": True,
        "flattenPaths": True,
        "useIndexes": False,
        "legacyOutput": True,
        "debug": False,
        "fast": False,
        "limitMemory": True,
        "currentProject": True,
        "silent": True,
        "ignore": False,
    }
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings_path
