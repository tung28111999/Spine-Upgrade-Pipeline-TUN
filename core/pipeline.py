from __future__ import annotations

import os
import shutil
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.archive_extractor import ARCHIVE_SUFFIXES, create_archive_from_folder, extract_archive_to_sibling_folder, extract_zip_inputs
from core.image_path import copy_images_for_project, patch_json_images_path, write_square_pack_settings
from core.logger import PipelineLogger, PipelineSummary
from core.normalizer import WorkingSetNormalizer
from core.runtime_export import build_unity_runtime_package, first_runtime_file, png_dimensions
from core.scanner import AssetScanner
from core.spine_cli import SpineCli
from core.version_detector import detect_spine_version, spine_line
from models.asset_job import AssetJob

CANONICAL_IMAGES_PATH = "./images/"


@dataclass(slots=True)
class PipelineConfig:
    input_dir: Path
    output_dir: Path
    old_spine_exe: Path
    new_spine_exe: Path
    old_spine_version: str = ""
    new_spine_version: str = ""
    input_archive: Path | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.input_archive is not None and str(self.input_archive):
            if not self.input_archive.is_file():
                errors.append("Archive file does not exist.")
            elif self.input_archive.suffix.lower() not in ARCHIVE_SUFFIXES:
                errors.append("Archive input must be a .zip or .rar file.")
        elif not self.input_dir.exists():
            errors.append("Input folder does not exist.")
        elif not self.input_dir.is_dir():
            errors.append("Input folder must be a folder.")
        if not self.old_spine_exe.is_file():
            errors.append("Old Spine executable path is missing or invalid.")
        if not self.new_spine_exe.is_file():
            errors.append("New Spine executable path is missing or invalid.")
        return errors


class SpineUpgradePipeline:
    def __init__(self, config: PipelineConfig, ui_log: Callable[[str], None] | None = None) -> None:
        self.config = config
        self.work_root = config.output_dir / ".work"
        self.logger = PipelineLogger(self.work_root, ui_log)
        self.scanner = AssetScanner()
        self.normalizer = WorkingSetNormalizer()
        self.new_spine = SpineCli(config.new_spine_exe, config.new_spine_version)

    def run(self) -> PipelineSummary:
        if self.config.input_archive is not None and str(self.config.input_archive):
            extracted_input = extract_archive_to_sibling_folder(self.config.input_archive)
            self.config.input_dir = extracted_input
            self.config.output_dir = extracted_input / "SpineNewVersion"
            self.work_root = self.config.output_dir / ".work"
            self.logger = PipelineLogger(self.work_root, self.logger.ui_log)

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._clean_visible_artifacts()
        self.logger.prepare()
        self.logger.info("Spine Upgrade Pipeline TUN")
        self.logger.info(f"Input: {self.config.input_dir}")
        self.logger.info(f"Output: {self.config.output_dir}")
        self.logger.info("Source Spine version: auto-detect per asset")
        self.logger.info(f"New Spine version: {self.config.new_spine_version or 'default'}")

        extracted_roots = extract_zip_inputs(self.config.input_dir, self.work_root / "extracted_zips")
        if extracted_roots:
            self.logger.info("Extracted zip inputs: " + "; ".join(str(path) for path in extracted_roots))

        jobs = self.scanner.scan(self.config.input_dir, extracted_roots)
        if not jobs:
            self.logger.error("No .json, .skel, .skel.bytes, .atlas, or .atlas.txt files were found in folders or zip files.")
            summary = self.logger.write_summary([])
            self._cleanup_work_root(self.work_root)
            return summary

        for job in jobs:
            job_work_root = self.work_root / job.folder_name
            source_root = job_work_root / "source"
            images_root = job_work_root / "images"
            old_projects_root = job_work_root / "spine_old"
            new_projects_root = self.config.output_dir / "spine_new" / job.folder_name
            raw_export_root = job_work_root / "export_raw"
            packed_atlas_root = job_work_root / "packed_atlas"
            export_root = self.config.output_dir / "export" / job.folder_name
            metadata_root = job_work_root / "metadata"

            self.logger.info(f"--- Job: {job.folder_name} ({job.name}) ---")
            if not job.has_required_files:
                job.status = "FAIL"
                job.message = ", ".join(job.missing_reasons())
                self.logger.error(f"{job.folder_name}: {job.message}")
                continue

            try:
                self.normalizer.copy_and_normalize(job, source_root)
                assert job.normalized_atlas_path is not None
                assert job.normalized_skeleton_path is not None
                job.detected_spine_version = detect_spine_version(job.normalized_skeleton_path)
                old_spine_version = spine_line(job.detected_spine_version)
                old_spine = SpineCli(self.config.old_spine_exe, old_spine_version)
                self.logger.info(f"Detected source Spine version: {job.detected_spine_version} -> {old_spine_version}.xx")

                unpack_result = old_spine.unpack_atlas(job.normalized_atlas_path, images_root)
                self.logger.command_result(unpack_result.label, unpack_result.command, unpack_result.returncode, unpack_result.stdout, unpack_result.stderr)
                if not unpack_result.ok:
                    raise RuntimeError("atlas unpack failed")

                job.old_project_path = old_projects_root / f"{job.name}_imported_old.spine"
                import_result = old_spine.import_skeleton(job.normalized_skeleton_path, job.old_project_path)
                self.logger.command_result(import_result.label, import_result.command, import_result.returncode, import_result.stdout, import_result.stderr)
                if not import_result.ok:
                    raise RuntimeError("old Spine import failed")

                project_images_dir = copy_images_for_project(images_root, new_projects_root, CANONICAL_IMAGES_PATH)
                pack_settings_path = write_square_pack_settings(project_images_dir)
                self.logger.info(f"New project images folder: {project_images_dir}")
                self.logger.info(f"Atlas pack settings: {pack_settings_path}")

                new_project_import_source = self._create_new_project_import_source(job, metadata_root)
                job.new_project_path = new_projects_root / f"{job.name}_imported_new.spine"
                new_project_result = self.new_spine.import_to_project(
                    new_project_import_source,
                    job.new_project_path,
                    "Create new Spine project",
                )
                self.logger.command_result(
                    new_project_result.label,
                    new_project_result.command,
                    new_project_result.returncode,
                    new_project_result.stdout,
                    new_project_result.stderr,
                )
                if not new_project_result.ok:
                    raise RuntimeError("new Spine project creation failed")

                job.export_dir = raw_export_root
                export_format = self._export_format_for(job.normalized_skeleton_path)
                self.logger.info(f"Export format: {export_format}")
                export_result = self.new_spine.export_runtime_data(job.new_project_path, job.export_dir, export_format)
                self.logger.command_result(export_result.label, export_result.command, export_result.returncode, export_result.stdout, export_result.stderr)
                if not export_result.ok:
                    raise RuntimeError("new Spine export failed")

                packed_atlas_dir = packed_atlas_root
                pack_result = self.new_spine.pack_atlas(
                    new_projects_root / "images",
                    packed_atlas_dir,
                    job.name,
                    job.new_project_path,
                )
                self.logger.command_result(pack_result.label, pack_result.command, pack_result.returncode, pack_result.stdout, pack_result.stderr)
                if not pack_result.ok:
                    raise RuntimeError("new Spine atlas pack failed")
                self._log_packed_atlas_size(packed_atlas_dir)
                try:
                    pack_settings_path.unlink(missing_ok=True)
                except OSError:
                    pass

                job.unity_runtime_dir = export_root
                unity_files = build_unity_runtime_package(job, job.unity_runtime_dir, packed_atlas_dir)
                self.logger.info("Export package: " + "; ".join(str(path) for path in unity_files))

                job.status = "PASS"
                job.message = "completed"
                self.logger.info(f"PASS: {job.folder_name}")
            except Exception as exc:
                job.status = "FAIL"
                job.message = str(exc)
                self.logger.error(f"{job.folder_name}: {job.message}")

        summary = self.logger.write_summary(jobs)
        self._archive_final_outputs()
        self.logger.info(f"Finished: {summary.passed_jobs} passed, {summary.failed_jobs} failed.")
        self._cleanup_work_root(self.work_root)
        return summary

    @staticmethod
    def _export_format_for(skeleton_path: Path) -> str:
        if skeleton_path.suffix.lower() == ".json":
            return "json"
        return "binary"

    @staticmethod
    def _runtime_suffix_for(skeleton_path: Path) -> str:
        if skeleton_path.suffix.lower() == ".json":
            return ".json"
        return ".skel"

    def _cleanup_work_root(self, work_root: Path) -> None:
        if not work_root.exists():
            return
        last_error: OSError | None = None
        for _ in range(5):
            try:
                shutil.rmtree(work_root, onerror=self._handle_remove_readonly)
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error is not None:
            self.logger.info(f"Could not clean temporary work folder {work_root}: {last_error}")

    def _log_packed_atlas_size(self, packed_atlas_dir: Path) -> None:
        for png_path in sorted(packed_atlas_dir.glob("*.png")):
            dimensions = png_dimensions(png_path)
            if dimensions is None:
                continue
            width, height = dimensions
            ratio = max(width, height) / max(1, min(width, height))
            if ratio > 1.5:
                self.logger.info(f"Packed atlas size: {png_path.name} {width}x{height} (ratio exceeds 1.5)")
            else:
                self.logger.info(f"Packed atlas size: {png_path.name} {width}x{height}")

    def _clean_visible_artifacts(self) -> None:
        if not self.config.output_dir.exists():
            return
        for path in self.config.output_dir.iterdir():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            except OSError:
                pass

    def _archive_final_outputs(self) -> None:
        archive_suffix = ".zip"
        if self.config.input_archive is not None and self.config.input_archive.suffix.lower() == ".rar":
            archive_suffix = ".rar"
        for folder_name in ("export", "spine_new"):
            folder = self.config.output_dir / folder_name
            if not folder.is_dir():
                continue
            archive_path = self.config.output_dir / f"{folder_name}{archive_suffix}"
            created_path = create_archive_from_folder(folder, archive_path)
            self.logger.info(f"Created archive: {created_path}")

    @staticmethod
    def _handle_remove_readonly(function, path: str, _exc_info) -> None:
        try:
            os.chmod(path, stat.S_IWRITE)
            function(path)
        except OSError:
            pass

    def _create_new_project_import_source(self, job: AssetJob, metadata_dir: Path) -> Path:
        if job.old_project_path is None:
            raise RuntimeError("old Spine project is missing")

        metadata_export_dir = metadata_dir / "json_probe"
        probe_result = self.new_spine.export_runtime_data(
            job.old_project_path,
            metadata_export_dir,
            "json",
            "Create patched JSON import source",
        )
        self.logger.command_result(probe_result.label, probe_result.command, probe_result.returncode, probe_result.stdout, probe_result.stderr)
        if not probe_result.ok:
            raise RuntimeError("could not create patched JSON import source for new Spine project")

        exported_json = first_runtime_file(metadata_export_dir, ".json")
        if exported_json is None:
            raise RuntimeError("JSON probe did not produce a .json file")

        if not patch_json_images_path(exported_json, CANONICAL_IMAGES_PATH):
            raise RuntimeError("could not patch JSON import source images path")
        self.logger.info(f"Patched new project import JSON images path: {CANONICAL_IMAGES_PATH}")
        return exported_json
