from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CommandResult:
    label: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class SpineCli:
    def __init__(self, executable: Path, version: str | None = None) -> None:
        self.executable = executable
        self.version = version

    def unpack_atlas(self, atlas_path: Path, output_images_dir: Path) -> CommandResult:
        output_images_dir.mkdir(parents=True, exist_ok=True)
        command = self._base_command() + [
            "--input",
            str(atlas_path.parent),
            "--output",
            str(output_images_dir),
            "--unpack",
            str(atlas_path),
        ]
        return self._run("Unpack atlas", command)

    def import_to_project(self, input_path: Path, project_path: Path, label: str = "Import to project") -> CommandResult:
        project_path.parent.mkdir(parents=True, exist_ok=True)
        command = self._base_command() + [
            "--input",
            str(input_path),
            "--output",
            str(project_path),
            "--import",
        ]
        return self._run(label, command)

    def import_skeleton(self, skeleton_path: Path, project_path: Path) -> CommandResult:
        return self.import_to_project(skeleton_path, project_path, "Import skeleton")

    def export_runtime_data(
        self,
        project_path: Path,
        export_dir: Path,
        export_format: str,
        label: str = "Export upgraded runtime data",
    ) -> CommandResult:
        export_dir.mkdir(parents=True, exist_ok=True)
        command = self._base_command() + [
            "--input",
            str(project_path),
            "--output",
            str(export_dir),
            "--export",
            export_format,
        ]
        return self._run(label, command)

    def pack_atlas(
        self,
        images_dir: Path,
        output_dir: Path,
        atlas_name: str,
        project_path: Path | None = None,
    ) -> CommandResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        command = self._base_command() + [
            "--input",
            str(images_dir),
            "--output",
            str(output_dir),
            "--pack",
            atlas_name,
        ]
        if project_path is not None:
            command.extend(["--project", str(project_path)])
        return self._run("Pack atlas", command)

    def _base_command(self) -> list[str]:
        command = [str(self.executable)]
        if self.version:
            command.extend(["--update", f"{self.version}.xx"])
        return command

    @staticmethod
    def _run(label: str, command: list[str]) -> CommandResult:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return CommandResult(
            label=label,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
