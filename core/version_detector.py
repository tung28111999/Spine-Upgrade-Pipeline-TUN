from __future__ import annotations

import json
import re
from pathlib import Path


VERSION_PATTERN = re.compile(rb"(?<!\d)([2-4]\.\d(?:\.\d{1,3})?)(?!\d)")


def detect_spine_version(skeleton_path: Path) -> str:
    if skeleton_path.suffix.lower() == ".json":
        return _detect_json_version(skeleton_path)
    return _detect_binary_version(skeleton_path)


def spine_line(version: str) -> str:
    match = re.match(r"^([2-4]\.\d)", version.strip())
    if not match:
        raise ValueError(f"Unsupported or unreadable Spine version: {version}")
    return match.group(1)


def _detect_json_version(json_path: Path) -> str:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    skeleton = data.get("skeleton", {})
    if not isinstance(skeleton, dict):
        raise ValueError("JSON skeleton is missing the skeleton object")
    version = skeleton.get("spine")
    if not version:
        raise ValueError("JSON skeleton is missing skeleton.spine")
    return str(version)


def _detect_binary_version(binary_path: Path) -> str:
    data = binary_path.read_bytes()
    match = VERSION_PATTERN.search(data[:4096]) or VERSION_PATTERN.search(data)
    if not match:
        raise ValueError("Could not detect Spine version from binary skeleton")
    return match.group(1).decode("ascii")
