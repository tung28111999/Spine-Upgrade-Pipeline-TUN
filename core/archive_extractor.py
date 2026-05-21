from __future__ import annotations

import zipfile
import shutil
import subprocess
from pathlib import Path


ARCHIVE_SUFFIXES = {".zip", ".rar"}


def extract_zip_inputs(input_dir: Path, extract_root: Path) -> list[Path]:
    extracted_dirs: list[Path] = []
    zip_paths = sorted(
        path
        for path in input_dir.rglob("*.zip")
        if path.is_file() and not any(part.lower() == "spinenewversion" for part in path.parts)
    )

    for zip_path in zip_paths:
        target_dir = extract_root / _safe_stem(zip_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                target_path = (target_dir / member.filename).resolve()
                if not _is_inside(target_dir.resolve(), target_path):
                    raise ValueError(f"Unsafe zip entry blocked: {member.filename}")
                archive.extract(member, target_dir)
        extracted_dirs.append(target_dir)

    return extracted_dirs


def extract_archive_to_sibling_folder(archive_path: Path) -> Path:
    target_dir = archive_path.with_suffix("")
    target_dir.mkdir(parents=True, exist_ok=True)
    extract_archive_to_folder(archive_path, target_dir)
    return target_dir


def extract_archive_to_folder(archive_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix.lower() == ".zip":
        _extract_zip(archive_path, target_dir)
    elif archive_path.suffix.lower() == ".rar":
        _extract_rar(archive_path, target_dir)
    else:
        raise ValueError("Input archive must be .zip or .rar")
    return target_dir


def create_archive_from_folder(folder_path: Path, archive_path: Path) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix.lower() == ".zip":
        _create_zip(folder_path, archive_path)
        return archive_path
    if archive_path.suffix.lower() == ".rar":
        created = _create_rar(folder_path, archive_path)
        if created is not None:
            return created
        fallback = archive_path.with_suffix(".zip")
        _create_zip(folder_path, fallback)
        return fallback
    raise ValueError("Output archive must be .zip or .rar")


def _create_zip(folder_path: Path, archive_path: Path) -> None:
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in folder_path.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(folder_path.parent))


def _create_rar(folder_path: Path, archive_path: Path) -> Path | None:
    tool = _find_rar_create_tool()
    if tool is None:
        return None
    if archive_path.exists():
        archive_path.unlink()
    completed = subprocess.run(
        [str(tool), "a", "-r", "-ep1", str(archive_path), str(folder_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0 or not archive_path.exists():
        return None
    return archive_path


def _extract_zip(zip_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target_path = (target_dir / member.filename).resolve()
            if not _is_inside(target_dir.resolve(), target_path):
                raise ValueError(f"Unsafe zip entry blocked: {member.filename}")
            archive.extract(member, target_dir)


def _extract_rar(rar_path: Path, target_dir: Path) -> None:
    tool = _find_rar_tool()
    if tool is None:
        raise RuntimeError("Cannot extract .rar: install 7-Zip, WinRAR, or unrar and add it to PATH.")

    exe_name = tool.name.lower()
    if exe_name in {"7z.exe", "7z"}:
        command = [str(tool), "x", "-y", f"-o{target_dir}", str(rar_path)]
    else:
        command = [str(tool), "x", "-y", str(rar_path), str(target_dir)]

    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"RAR extract failed:\n{completed.stdout}\n{completed.stderr}".strip())


def _find_rar_tool() -> Path | None:
    for name in ("7z", "WinRAR", "UnRAR", "unrar"):
        found = shutil.which(name)
        if found:
            return Path(found)

    candidates = [
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files\WinRAR\WinRAR.exe"),
        Path(r"C:\Program Files\WinRAR\UnRAR.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\WinRAR\WinRAR.exe"),
        Path(r"C:\Program Files (x86)\WinRAR\UnRAR.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _find_rar_create_tool() -> Path | None:
    for name in ("rar", "WinRAR"):
        found = shutil.which(name)
        if found:
            return Path(found)
    candidates = [
        Path(r"C:\Program Files\WinRAR\Rar.exe"),
        Path(r"C:\Program Files\WinRAR\WinRAR.exe"),
        Path(r"C:\Program Files (x86)\WinRAR\Rar.exe"),
        Path(r"C:\Program Files (x86)\WinRAR\WinRAR.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _safe_stem(path: Path) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in path.stem)
    return safe or "zip_input"


def _is_inside(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
