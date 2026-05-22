from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from models.asset_job import AssetJob

SKELETON_SUFFIXES = (".json", ".skel", ".skel.bytes")
ATLAS_SUFFIXES = (".atlas", ".atlas.txt")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class AssetScanner:
    def scan(self, input_dir: Path, extra_roots: list[Path] | None = None) -> list[AssetJob]:
        skeletons: dict[tuple[Path, str], Path] = {}
        atlases: dict[tuple[Path, str], Path] = {}
        images_by_dir: dict[Path, list[Path]] = defaultdict(list)

        roots = [input_dir] + list(extra_roots or [])
        for root in roots:
            self._scan_root(root, skeletons, atlases, images_by_dir)

        keys = sorted(set(skeletons) | set(atlases), key=lambda item: (str(item[0]).lower(), item[1].lower()))
        asset_count_by_parent: dict[Path, int] = defaultdict(int)
        for parent, _asset_name in keys:
            asset_count_by_parent[parent] += 1

        jobs: list[AssetJob] = []
        used_output_names: set[str] = set()
        for parent, asset_name in keys:
            key = (parent, asset_name)
            skeleton = skeletons.get(key)
            atlas = atlases.get(key)
            image_dir = atlas.parent if atlas else (skeleton.parent if skeleton else input_dir)
            images = self._atlas_images(atlas, images_by_dir.get(image_dir, [])) if atlas else images_by_dir.get(image_dir, [])
            output_name = self.output_name(
                input_dir,
                parent,
                asset_name,
                used_output_names,
                use_asset_name=asset_count_by_parent[parent] > 1,
            )
            jobs.append(
                AssetJob(
                    name=asset_name,
                    output_name=output_name,
                    skeleton_path=skeleton,
                    atlas_path=atlas,
                    image_paths=sorted(images),
                )
            )

        return jobs

    def _scan_root(
        self,
        root: Path,
        skeletons: dict[tuple[Path, str], Path],
        atlases: dict[tuple[Path, str], Path],
        images_by_dir: dict[Path, list[Path]],
    ) -> None:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if self._is_ignored_metadata(path):
                continue
            if path.suffix.lower() == ".zip":
                continue
            if any(part.lower() == "spinenewversion" for part in path.parts):
                continue
            lower_name = path.name.lower()
            key = (path.parent, self.asset_key(path))
            if lower_name.endswith(SKELETON_SUFFIXES):
                skeletons[key] = path
            elif lower_name.endswith(ATLAS_SUFFIXES):
                atlases[key] = path
            elif path.suffix.lower() in IMAGE_SUFFIXES:
                images_by_dir[path.parent].append(path)

    @staticmethod
    def asset_key(path: Path) -> str:
        name = path.name
        for suffix in (".skel.bytes", ".atlas.txt", ".json", ".skel", ".atlas"):
            if name.lower().endswith(suffix):
                return name[: -len(suffix)]
        return path.stem

    @staticmethod
    def output_name(
        input_dir: Path,
        asset_dir: Path,
        asset_name: str,
        used: set[str],
        use_asset_name: bool = False,
    ) -> str:
        base = asset_name if use_asset_name else (asset_dir.name or asset_name)

        candidate = base
        index = 2
        while candidate.lower() in used:
            candidate = f"{base}_{index}"
            index += 1
        used.add(candidate.lower())
        return candidate

    @staticmethod
    def _is_ignored_metadata(path: Path) -> bool:
        return path.name.startswith("._") or any(part == "__MACOSX" for part in path.parts)

    @staticmethod
    def _atlas_images(atlas_path: Path | None, nearby_images: list[Path]) -> list[Path]:
        if atlas_path is None or not nearby_images:
            return []
        by_name = {path.name: path for path in nearby_images}
        used: list[Path] = []
        try:
            for raw_line in atlas_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or ":" in line:
                    continue
                if line in by_name:
                    used.append(by_name[line])
        except OSError:
            return nearby_images
        return used or nearby_images
