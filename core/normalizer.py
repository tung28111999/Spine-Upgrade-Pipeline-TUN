from __future__ import annotations

import shutil
from pathlib import Path

from models.asset_job import AssetJob


class WorkingSetNormalizer:
    def copy_and_normalize(self, job: AssetJob, source_root: Path) -> AssetJob:
        job_dir = source_root / job.name
        job_dir.mkdir(parents=True, exist_ok=True)
        job.source_dir = job_dir

        if job.skeleton_path:
            skeleton_target = job_dir / self._normalized_name(job.skeleton_path.name)
            shutil.copy2(job.skeleton_path, skeleton_target)
            job.normalized_skeleton_path = skeleton_target

        if job.atlas_path:
            atlas_target = job_dir / self._normalized_name(job.atlas_path.name)
            shutil.copy2(job.atlas_path, atlas_target)
            job.normalized_atlas_path = atlas_target

        for image in job.image_paths:
            shutil.copy2(image, job_dir / image.name)

        return job

    @staticmethod
    def _normalized_name(name: str) -> str:
        lower = name.lower()
        if lower.endswith(".skel.bytes"):
            return name[: -len(".bytes")]
        if lower.endswith(".atlas.txt"):
            return name[: -len(".txt")]
        return name
