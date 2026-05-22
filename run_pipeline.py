from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.headless_pipeline import HeadlessConfig, HeadlessPipeline

EXIT_SUCCESS = 0
EXIT_VALIDATION = 1
EXIT_PIPELINE_FAILED = 2
EXIT_SPINE_CLI_FAILED = 3
EXIT_UNEXPECTED = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Spine Upgrade Pipeline TUN without opening the UI.")
    parser.add_argument("--input", required=True, help="Input folder or .zip/.rar archive containing exported Spine assets.")
    parser.add_argument("--output", required=True, help="Output folder for generated files.")
    parser.add_argument("--old", default=None, help="Old/source Spine version. Defaults to config default_old_version.")
    parser.add_argument("--new", required=True, help="Target Spine version.")
    parser.add_argument("--config", default="config.json", help="Path to config.json.")
    parser.add_argument("--export-json", action="store_true", help="Export upgraded JSON runtime data.")
    parser.add_argument("--export-binary", action="store_true", help="Export upgraded binary runtime data.")
    parser.add_argument("--pack", action="store_true", help="Pack atlas output.")
    parser.add_argument("--no-pack", action="store_true", help="Skip atlas packing.")
    parser.add_argument("--archive-format", choices=("zip", "rar"), default=None, help="Archive final spine_new and export folders.")
    parser.add_argument("--skip-spine-new", action="store_true", help="Skip creating upgraded .spine project; useful for Dev export-only jobs.")
    parser.add_argument("--final-only", action="store_true", help="After success, keep only spine_new and export.")
    parser.add_argument("--verbose", action="store_true", help="Print detailed pipeline logs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config_path = Path(args.config)
        config = load_config(config_path)
        validation_errors = validate_args(args, config)
        if validation_errors:
            for error in validation_errors:
                print(f"VALIDATION ERROR: {error}", file=sys.stderr)
            return EXIT_VALIDATION

        old_version = args.old if args.old is not None else str(config.get("default_old_version", "auto"))
        old_version_for_path = None if old_version.lower() == "auto" else old_version
        new_version = args.new

        export_json, export_binary = resolve_export_modes(args, config)
        pack = resolve_pack_mode(args, config)
        archive_format = args.archive_format or archive_format_from_input(Path(args.input), config)

        old_exe = resolve_spine_executable(config, old_version_for_path, fallback_version=new_version)
        new_exe = resolve_spine_executable(config, new_version, fallback_version=new_version)

        output_dir = Path(args.output)
        runner_config = HeadlessConfig(
            input_dir=Path(args.input),
            output_dir=output_dir,
            old_spine_exe=old_exe,
            new_spine_exe=new_exe,
            old_version=old_version_for_path,
            new_version=new_version,
            export_json=export_json,
            export_binary=export_binary,
            pack=pack,
            cleanup_temp=bool(config.get("cleanup_temp", True)),
            final_only=args.final_only,
            archive_format=archive_format,
            create_spine_new=not args.skip_spine_new,
        )

        print(f"Input: {runner_config.input_dir}")
        print(f"Output: {runner_config.output_dir}")
        print(f"Old version: {old_version}")
        print(f"New version: {new_version}")
        print(f"Export JSON: {export_json}")
        print(f"Export binary: {export_binary}")
        print(f"Pack atlas: {pack}")

        pipeline = HeadlessPipeline(runner_config, print if args.verbose else None)
        result = pipeline.run()
        if result.success:
            if result.summary_path is not None:
                print(f"SUCCESS: summary written to {result.summary_path}")
            else:
                print("SUCCESS: final output written.")
            return EXIT_SUCCESS

        print(f"FAILED: summary written to {result.summary_path}", file=sys.stderr)
        return EXIT_SPINE_CLI_FAILED if result.spine_cli_failed else EXIT_PIPELINE_FAILED
    except ValidationError as exc:
        print(f"VALIDATION ERROR: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return EXIT_UNEXPECTED


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise ValidationError(f"Config file does not exist: {config_path}")
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Config file is not valid JSON: {exc}") from exc


def validate_args(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    input_dir = Path(args.input)
    if not input_dir.exists():
        errors.append(f"Input path does not exist: {input_dir}")
    elif not input_dir.is_dir() and input_dir.suffix.lower() not in {".zip", ".rar"}:
        errors.append(f"Input must be a folder, .zip, or .rar file: {input_dir}")
    if args.pack and args.no_pack:
        errors.append("Use either --pack or --no-pack, not both.")

    versions = config.get("spine_versions")
    if not isinstance(versions, dict) or not versions:
        errors.append("config.json must contain a non-empty spine_versions mapping.")

    allowed = config.get("allowed_target_versions", [])
    if args.new not in allowed:
        errors.append(f"Target version {args.new} is not in allowed_target_versions.")

    old_version = args.old if args.old is not None else str(config.get("default_old_version", "auto"))
    if old_version.lower() != "auto" and old_version not in versions:
        errors.append(f"Old version {old_version} is not configured in spine_versions.")
    if args.new not in versions:
        errors.append(f"New version {args.new} is not configured in spine_versions.")

    if isinstance(versions, dict):
        versions_to_check = {args.new}
        if old_version.lower() != "auto":
            versions_to_check.add(old_version)
        for version in sorted(versions_to_check):
            path = Path(str(versions.get(version, "")))
            if not path.is_file():
                errors.append(f"Spine executable for version {version} does not exist: {path}")

    return errors


def resolve_spine_executable(config: dict[str, Any], version: str | None, fallback_version: str) -> Path:
    versions = config.get("spine_versions", {})
    selected_version = version or fallback_version
    path = Path(str(versions.get(selected_version, "")))
    if not path.is_file():
        raise ValidationError(f"Spine executable for version {selected_version} does not exist: {path}")
    return path


def resolve_export_modes(args: argparse.Namespace, config: dict[str, Any]) -> tuple[bool, bool]:
    if args.export_json or args.export_binary:
        return args.export_json, args.export_binary
    return bool(config.get("default_export_json", False)), bool(config.get("default_export_binary", True))


def resolve_pack_mode(args: argparse.Namespace, config: dict[str, Any]) -> bool:
    if args.pack:
        return True
    if args.no_pack:
        return False
    return bool(config.get("default_pack", True))


def archive_format_from_input(input_path: Path, config: dict[str, Any]) -> str:
    if input_path.suffix.lower() == ".rar":
        return "rar"
    if input_path.suffix.lower() == ".zip":
        return "zip"
    return str(config.get("default_archive_format", "zip"))


class ValidationError(RuntimeError):
    pass


if __name__ == "__main__":
    raise SystemExit(main())
