from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QTransform


@dataclass(slots=True)
class AtlasRegion:
    name: str
    page: str
    bounds: tuple[int, int, int, int]
    rotate: int = 0
    offsets: tuple[int, int, int, int] | None = None


def unpack_atlas_fallback(atlas_path: Path, output_dir: Path) -> list[Path]:
    regions = _parse_atlas(atlas_path)
    if not regions:
        raise ValueError("Atlas fallback unpack found no regions.")

    output_dir.mkdir(parents=True, exist_ok=True)
    page_cache: dict[str, QImage] = {}
    written: list[Path] = []
    for region in regions:
        page_image = page_cache.get(region.page)
        if page_image is None:
            page_path = atlas_path.parent / region.page
            page_image = QImage(str(page_path))
            if page_image.isNull():
                raise ValueError(f"Could not read atlas page image: {page_path}")
            page_cache[region.page] = page_image

        x, y, width, height = region.bounds
        cropped = page_image.copy(x, y, width, height)
        if cropped.isNull():
            raise ValueError(f"Could not crop atlas region: {region.name}")

        if region.rotate in (90, 270):
            cropped = cropped.transformed(QTransform().rotate(-region.rotate), Qt.SmoothTransformation)

        if region.offsets is not None:
            left, bottom, original_width, original_height = region.offsets
            canvas = QImage(original_width, original_height, QImage.Format_ARGB32)
            canvas.fill(QColor(0, 0, 0, 0))
            draw_x = left
            draw_y = original_height - bottom - cropped.height()
            _blit(canvas, cropped, draw_x, draw_y)
            cropped = canvas

        target = _region_output_path(output_dir, region.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not cropped.save(str(target)):
            raise ValueError(f"Could not write unpacked image: {target}")
        written.append(target)
    return written


def _parse_atlas(atlas_path: Path) -> list[AtlasRegion]:
    lines = atlas_path.read_text(encoding="utf-8", errors="replace").splitlines()
    regions: list[AtlasRegion] = []
    current_page = ""
    current_name = ""
    current_props: dict[str, str] = {}

    def flush_region() -> None:
        nonlocal current_name, current_props
        if not current_name or "bounds" not in current_props:
            current_name = ""
            current_props = {}
            return
        bounds = _parse_ints(current_props["bounds"], 4)
        rotate = _parse_rotate(current_props.get("rotate", "0"))
        offsets = _parse_ints(current_props["offsets"], 4) if "offsets" in current_props else None
        regions.append(AtlasRegion(current_name, current_page, bounds, rotate, offsets))
        current_name = ""
        current_props = {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_region()
            current_page = ""
            continue

        key, sep, value = line.partition(":")
        if not sep:
            if current_name:
                flush_region()
            if line.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                current_page = line
            else:
                current_name = line
                current_props = {}
            continue

        key = key.strip()
        value = value.strip()
        if current_name:
            current_props[key] = value

    flush_region()
    return regions


def _parse_ints(value: str, count: int) -> tuple[int, ...]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != count:
        raise ValueError(f"Expected {count} integer values, got: {value}")
    return tuple(int(part) for part in parts)


def _parse_rotate(value: str) -> int:
    normalized = value.strip().lower()
    if normalized in ("true", "90"):
        return 90
    if normalized == "270":
        return 270
    return 0


def _region_output_path(output_dir: Path, region_name: str) -> Path:
    safe_parts = [part for part in region_name.replace("\\", "/").split("/") if part]
    if not safe_parts:
        safe_parts = ["region"]
    return output_dir.joinpath(*safe_parts).with_suffix(".png")


def _blit(target: QImage, source: QImage, x_offset: int, y_offset: int) -> None:
    for y in range(source.height()):
        target_y = y + y_offset
        if target_y < 0 or target_y >= target.height():
            continue
        for x in range(source.width()):
            target_x = x + x_offset
            if target_x < 0 or target_x >= target.width():
                continue
            target.setPixelColor(target_x, target_y, source.pixelColor(x, y))
