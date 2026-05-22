from __future__ import annotations

import json
import os
import shutil
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.atlas_unpacker import unpack_atlas_fallback
from core.archive_extractor import ARCHIVE_SUFFIXES, create_archive_from_folder, extract_archive_to_folder
from core.image_path import copy_images_for_project, patch_json_images_path, write_square_pack_settings
from core.logger import PipelineLogger
from core.normalizer import WorkingSetNormalizer
from core.runtime_export import build_unity_runtime_package, first_runtime_file, png_dimensions
from core.scanner import AssetScanner
from core.spine_cli import SpineCli
from core.version_detector import detect_spine_version, spine_line
from models.asset_job import AssetJob

CANONICAL_IMAGES_PATH = "./images/"


@dataclass(slots=True)
class HeadlessConfig:
    input_dir: Path
    output_dir: Path
    old_spine_exe: Path
    new_spine_exe: Path
    old_version: str | None
    new_version: str
    export_json: bool
    export_binary: bool
    pack: bool
    cleanup_temp: bool = True
    final_only: bool = False
    archive_format: str = "zip"
    create_spine_new: bool = True


@dataclass(slots=True)
class HeadlessResult:
    success: bool
    spine_cli_failed: bool = False
    warnings: list[str] = field(default_factory=list)
    jobs: list[dict] = field(default_factory=list)
    summary_path: Path | None = None


class HeadlessPipeline:
    def __init__(self, config: HeadlessConfig, console_log: Callable[[str], None] | None = None) -> None:
        self.config = config
        self.console_log = console_log
        self.logger = PipelineLogger(config.output_dir, console_log)
        self.scanner = AssetScanner()
        self.normalizer = WorkingSetNormalizer()
        self.new_spine = SpineCli(config.new_spine_exe, config.new_version)
        self.warnings: list[str] = [
            "Importing exported skeleton data may not perfectly reconstruct the original .spine project if nonessential/editor data is missing."
        ]

    def run(self) -> HeadlessResult:
        self._prepare_output()
        self.logger.prepare()
        self.logger.info("Spine Upgrade Pipeline TUN - Headless")
        self.logger.info(f"Input: {self.config.input_dir}")
        self.logger.info(f"Output: {self.config.output_dir}")

        scan_input_dir = self.config.input_dir
        if self.config.input_dir.is_file() and self.config.input_dir.suffix.lower() in ARCHIVE_SUFFIXES:
            scan_input_dir = extract_archive_to_folder(self.config.input_dir, self.config.output_dir / ".work" / "input_archive")
            self.logger.info(f"Extracted input archive to: {scan_input_dir}")

        jobs = self.scanner.scan(scan_input_dir)
        if not jobs:
            return self._finish([], False, "No Spine assets were found.")

        jobs = sorted(jobs, key=lambda job: (job.folder_name.lower(), job.name.lower()))
        spine_cli_failed = False
        for job in jobs:
            try:
                self._run_job(job)
            except SpineCliFailed as exc:
                spine_cli_failed = True
                job.status = "FAIL"
                job.message = str(exc)
                self.logger.error(f"{job.folder_name}: {job.message}")
            except Exception as exc:
                job.status = "FAIL"
                job.message = str(exc)
                self.logger.error(f"{job.folder_name}: {job.message}")

        success = all(job.status != "FAIL" for job in jobs)
        return self._finish(jobs, success, spine_cli_failed=spine_cli_failed)

    def _run_job(self, job: AssetJob) -> None:
        self.logger.info(f"--- Job: {job.folder_name} ({job.name}) ---")
        if not job.has_required_files:
            raise ValueError(", ".join(job.missing_reasons()))

        source_root = self.config.output_dir / "source"
        images_root = self.config.output_dir / "images"
        old_projects_root = self.config.output_dir / "spine_old"
        new_projects_root = self.config.output_dir / "spine_new"
        raw_export_root = self.config.output_dir / ".work" / "export_raw" / job.folder_name
        metadata_root = self.config.output_dir / ".work" / "metadata"
        packed_atlas_root = self.config.output_dir / ".work" / "packed_atlas"
        export_root = self.config.output_dir / "export"

        self.normalizer.copy_and_normalize(job, source_root)
        assert job.normalized_atlas_path is not None
        assert job.normalized_skeleton_path is not None

        detected_version = detect_spine_version(job.normalized_skeleton_path)
        job.detected_spine_version = detected_version
        old_version = self.config.old_version or spine_line(detected_version)
        if old_version == self.config.new_version:
            self._copy_same_version_job(job)
            job.status = "SKIPPED"
            job.message = f"source version {detected_version} is already target {self.config.new_version}"
            self.logger.info(f"SKIPPED: {job.folder_name}: {job.message}")
            return

        old_spine = SpineCli(self.config.old_spine_exe, old_version)
        self.logger.info(f"Detected source Spine version: {detected_version}")
        self.logger.info(f"Old Spine line: {old_version}.xx")
        self.logger.info(f"New Spine line: {self.config.new_version}.xx")

        self._unpack_atlas(old_spine, job.normalized_atlas_path, images_root / job.name)

        job.old_project_path = old_projects_root / f"{job.name}_imported_old.spine"
        self._run_cli(old_spine.import_skeleton(job.normalized_skeleton_path, job.old_project_path), "old Spine import failed")

        pack_images_dir = images_root / job.name
        pack_project_path = job.old_project_path
        pack_settings_path = write_square_pack_settings(pack_images_dir)

        if self.config.create_spine_new:
            project_images_dir = copy_images_for_project(images_root / job.name, new_projects_root / job.name, CANONICAL_IMAGES_PATH)
            try:
                pack_settings_path.unlink(missing_ok=True)
            except OSError:
                pass
            pack_settings_path = write_square_pack_settings(project_images_dir)
            self.logger.info(f"New project images folder: {project_images_dir}")

            new_project_import_source = self._create_new_project_import_source(job, metadata_root / job.name)
            job.new_project_path = new_projects_root / job.name / f"{job.name}_imported_new.spine"
            self._run_cli(
                self.new_spine.import_to_project(new_project_import_source, job.new_project_path, "Create new Spine project"),
                "new Spine project creation failed",
            )
            export_project_path = job.new_project_path
            pack_images_dir = new_projects_root / job.name / "images"
            pack_project_path = job.new_project_path
        else:
            export_project_path = job.old_project_path
            self.logger.info("Dev fast mode: skipping new .spine project creation.")

        export_formats = self._export_formats(job.normalized_skeleton_path)
        for export_format in export_formats:
            export_dir = raw_export_root / export_format
            self._run_cli(
                self.new_spine.export_runtime_data(export_project_path, export_dir, export_format),
                f"new Spine {export_format} export failed",
            )

        if self.config.pack:
            packed_atlas_dir = packed_atlas_root / job.name
            self._run_cli(
                self.new_spine.pack_atlas(pack_images_dir, packed_atlas_dir, job.name, pack_project_path),
                "new Spine atlas pack failed",
            )
            self._log_packed_atlas_size(packed_atlas_dir)
        else:
            packed_atlas_dir = source_root / job.name

        try:
            pack_settings_path.unlink(missing_ok=True)
        except OSError:
            pass

        job.export_dir = self._preferred_raw_export_dir(raw_export_root, export_formats)
        job.unity_runtime_dir = export_root / job.folder_name
        unity_files = build_unity_runtime_package(job, job.unity_runtime_dir, packed_atlas_dir)
        self.logger.info("Export package: " + "; ".join(str(path) for path in unity_files))

        job.status = "PASS"
        job.message = "completed"

    def _create_new_project_import_source(self, job: AssetJob, metadata_dir: Path) -> Path:
        if job.old_project_path is None:
            raise RuntimeError("old Spine project is missing")
        metadata_export_dir = metadata_dir / "json_probe"
        result = self.new_spine.export_runtime_data(
            job.old_project_path,
            metadata_export_dir,
            "json",
            "Create patched JSON import source",
        )
        self._run_cli(result, "could not create patched JSON import source for new Spine project")
        exported_json = first_runtime_file(metadata_export_dir, ".json")
        if exported_json is None:
            raise RuntimeError("JSON probe did not produce a .json file")
        if not patch_json_images_path(exported_json, CANONICAL_IMAGES_PATH):
            raise RuntimeError("could not patch JSON import source images path")
        self.logger.info(f"Patched new project import JSON images path: {CANONICAL_IMAGES_PATH}")
        return exported_json

    def _run_cli(self, result, failure_message: str) -> None:
        self.logger.command_result(result.label, result.command, result.returncode, result.stdout, result.stderr)
        if not result.ok:
            raise SpineCliFailed(failure_message)

    def _unpack_atlas(self, spine: SpineCli, atlas_path: Path, images_dir: Path) -> None:
        result = spine.unpack_atlas(atlas_path, images_dir)
        self.logger.command_result(result.label, result.command, result.returncode, result.stdout, result.stderr)
        if result.ok:
            return
        self.logger.info("Spine atlas unpack failed. Trying internal atlas unpack fallback.")
        fallback_images = unpack_atlas_fallback(atlas_path, images_dir)
        self.logger.info(f"PASS: Internal atlas unpack fallback wrote {len(fallback_images)} image(s).")

    def _export_formats(self, skeleton_path: Path) -> list[str]:
        formats: list[str] = []
        if self.config.export_json:
            formats.append("json")
        if self.config.export_binary:
            formats.append("binary")
        if not formats:
            formats.append("json" if skeleton_path.suffix.lower() == ".json" else "binary")
        return formats

    @staticmethod
    def _preferred_raw_export_dir(raw_export_root: Path, export_formats: list[str]) -> Path:
        preferred = "json" if "json" in export_formats else export_formats[0]
        return raw_export_root / preferred

    def _log_packed_atlas_size(self, packed_atlas_dir: Path) -> None:
        for png_path in sorted(packed_atlas_dir.glob("*.png")):
            dimensions = png_dimensions(png_path)
            if dimensions is None:
                continue
            width, height = dimensions
            ratio = max(width, height) / max(1, min(width, height))
            suffix = " (ratio exceeds 1.5)" if ratio > 1.5 else ""
            self.logger.info(f"Packed atlas size: {png_path.name} {width}x{height}{suffix}")

    def _prepare_output(self) -> None:
        folders = ["source", "images", "spine_old", "export", "logs", ".work"]
        if self.config.create_spine_new:
            folders.append("spine_new")
        for folder in folders:
            path = self.config.output_dir / folder
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        if not self.config.create_spine_new:
            self._cleanup_path(self.config.output_dir / "spine_new")

    def _finish(
        self,
        jobs: list[AssetJob],
        success: bool,
        message: str = "",
        spine_cli_failed: bool = False,
    ) -> HeadlessResult:
        if message:
            self.logger.error(message)
        summary_path = self._write_summary_json(jobs, success)
        if success:
            self._archive_final_outputs()
        if self.config.cleanup_temp:
            self._cleanup_path(self.config.output_dir / ".work")
        if self.config.final_only and success:
            self._clean_debug_outputs()
            summary_path = None
        return HeadlessResult(
            success=success,
            spine_cli_failed=spine_cli_failed,
            warnings=self.warnings,
            jobs=[self._job_summary(job) for job in jobs],
            summary_path=summary_path,
        )

    def _write_summary_json(self, jobs: list[AssetJob], success: bool) -> Path:
        summary_path = self.config.output_dir / "summary.json"
        data = {
            "success": success,
            "warning": self.warnings[0],
            "warnings": self.warnings,
            "jobs": [self._job_summary(job) for job in jobs],
        }
        summary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return summary_path

    def _clean_debug_outputs(self) -> None:
        for name in ("source", "images", "spine_old", "logs", "summary.json"):
            self._cleanup_path(self.config.output_dir / name)

    def _archive_final_outputs(self) -> None:
        suffix = ".rar" if self.config.archive_format.lower() == "rar" else ".zip"
        folder_names = ["export", "same_version"]
        if self.config.create_spine_new:
            folder_names.insert(0, "spine_new")
        for folder_name in folder_names:
            folder_path = self.config.output_dir / folder_name
            if not folder_path.is_dir():
                continue
            archive_path = self.config.output_dir / f"{folder_name}{suffix}"
            created_path = create_archive_from_folder(folder_path, archive_path)
            self.logger.info(f"Created archive: {created_path}")

    def _cleanup_path(self, path: Path) -> None:
        if not path.exists():
            return
        for _ in range(5):
            try:
                if path.is_dir():
                    shutil.rmtree(path, onerror=self._handle_remove_readonly)
                else:
                    path.unlink()
                return
            except OSError:
                time.sleep(0.5)

    @staticmethod
    def _handle_remove_readonly(function, path: str, _exc_info) -> None:
        try:
            os.chmod(path, stat.S_IWRITE)
            function(path)
        except OSError:
            pass

    @staticmethod
    def _job_summary(job: AssetJob) -> dict:
        return {
            "name": job.name,
            "output_name": job.folder_name,
            "status": job.status,
            "message": job.message,
            "source_version": job.detected_spine_version,
            "skeleton": str(job.skeleton_path or ""),
            "atlas": str(job.atlas_path or ""),
            "spine_new": str(job.new_project_path or ""),
            "export": str(job.unity_runtime_dir or ""),
        }

    def _copy_same_version_job(self, job: AssetJob) -> None:
        target_dir = self.config.output_dir / "same_version" / job.folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in [job.skeleton_path, job.atlas_path, *job.image_paths]:
            if source is not None and source.is_file():
                shutil.copy2(source, target_dir / source.name)


class SpineCliFailed(RuntimeError):
    pass
