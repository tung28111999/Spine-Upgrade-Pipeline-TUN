from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from models.asset_job import AssetJob


@dataclass(slots=True)
class PipelineSummary:
    total_jobs: int = 0
    passed_jobs: int = 0
    failed_jobs: int = 0


class PipelineLogger:
    def __init__(self, output_dir: Path, ui_log: Callable[[str], None] | None = None) -> None:
        self.output_dir = output_dir
        self.log_dir = output_dir / "logs"
        self.process_log = self.log_dir / "process.log"
        self.error_log = self.log_dir / "errors.log"
        self.ui_log = ui_log

    def prepare(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.process_log.write_text("", encoding="utf-8")
        self.error_log.write_text("", encoding="utf-8")

    def info(self, message: str) -> None:
        self._write(self.process_log, message)
        if self.ui_log:
            self.ui_log(message)

    def error(self, message: str) -> None:
        line = f"FAIL: {message}"
        self._write(self.process_log, line)
        self._write(self.error_log, line)
        if self.ui_log:
            self.ui_log(line)

    def command_result(self, label: str, command: list[str], returncode: int, stdout: str, stderr: str) -> None:
        status = "PASS" if returncode == 0 else "FAIL"
        self.info(f"{status}: {label}")
        self.info("COMMAND: " + " ".join(f'"{part}"' if " " in part else part for part in command))
        if stdout.strip():
            self.info("STDOUT:\n" + stdout.rstrip())
        if stderr.strip():
            self.info("STDERR:\n" + stderr.rstrip())
        if returncode != 0:
            self._write(self.error_log, f"{label} failed with exit code {returncode}\n{stderr}\n")

    def write_summary(self, jobs: Iterable[AssetJob]) -> PipelineSummary:
        rows = list(jobs)
        summary = PipelineSummary(total_jobs=len(rows))
        summary.passed_jobs = sum(1 for job in rows if job.status == "PASS")
        summary.failed_jobs = summary.total_jobs - summary.passed_jobs

        with (self.output_dir / "summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "name",
                    "status",
                    "message",
                    "skeleton",
                    "atlas",
                    "images",
                    "old_project",
                    "new_project",
                    "export_dir",
                ],
            )
            writer.writeheader()
            for job in rows:
                writer.writerow(
                    {
                        "name": job.name,
                        "status": job.status,
                        "message": job.message,
                        "skeleton": str(job.skeleton_path or ""),
                        "atlas": str(job.atlas_path or ""),
                        "images": ";".join(str(path) for path in job.image_paths),
                        "old_project": str(job.old_project_path or ""),
                        "new_project": str(job.new_project_path or ""),
                        "export_dir": str(job.unity_runtime_dir or ""),
                    }
                )
        return summary

    @staticmethod
    def _write(path: Path, message: str) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
