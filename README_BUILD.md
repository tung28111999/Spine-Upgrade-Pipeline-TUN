# Build Guide

This project can be packaged for Windows with PyInstaller. Spine itself is not bundled and must be installed/licensed separately on the target machine.

## Create A Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

## Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## Build

Run:

```powershell
build_windows.bat
```

The build uses PyInstaller `onedir` mode by default. Output is written to:

```text
dist/SpineUpgradePipelineTUN/
```

## Test The Built App

Run:

```powershell
dist\SpineUpgradePipelineTUN\SpineUpgradePipelineTUN.exe
```

Then verify:

- The UI opens.
- Dropdown icons render correctly.
- You can choose a local Spine executable.
- A small known test asset processes successfully.

## Notes

- Do not bundle `Spine.exe`, `Spine.com`, Spine license files, or local Spine user data.
- Users must install and license Spine themselves.
- Local `config.json`, job folders, logs, and build outputs should not be committed.
