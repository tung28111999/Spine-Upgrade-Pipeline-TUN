# Spine Upgrade Pipeline TUN

Spine Upgrade Pipeline TUN is a small Python/PySide6 desktop utility for updating Spine runtime assets to a newer Spine version when you only have exported files:

- `.json` or `.skel.bytes`
- `.atlas.txt`
- atlas PNG images

It is useful when the original `.spine` project is missing, but the exported runtime files still need to be upgraded for Unity or another runtime pipeline.

## What It Does

- Detects the source Spine version from `.json` or `.skel.bytes`.
- Copies input files to a temporary working folder without modifying originals.
- Uses Spine CLI to import old runtime data.
- Exports upgraded runtime data with the selected target Spine version.
- Rebuilds Unity-ready output:
  - `.json` or `.skel.bytes`
  - `.atlas.txt`
  - atlas PNG images
- Supports single assets, batch folders, `.zip`, and `.rar`.
- Creates upgraded `.spine` files when possible.

## Important Notes

- Spine is not included.
- Users must install Spine separately and use their own valid Spine license.
- Open Spine Launcher first and make sure the source/target versions can run before using this tool.
- Imported runtime data may not perfectly reconstruct the original `.spine` project if editor/nonessential data is missing.
- This project is unofficial and is not affiliated with Esoteric Software.
- Exported atlas textures use premultiplied alpha. In Unity Linear Color Space, use the matching Spine PMA texture/material workflow, otherwise colors may look washed out.

## Disclaimer

This is an unofficial community tool. It is not affiliated with, endorsed by, or sponsored by Esoteric Software.

Spine is a separate commercial product by Esoteric Software. This repository does not include Spine, Spine CLI, Spine executables, or any Spine license files.

Users must install Spine separately and use their own valid Spine license.

When importing exported skeleton data back into Spine, the reconstructed `.spine` project may not perfectly match the original project if nonessential/editor data is missing.

## Requirements

- Windows
- Python 3.10+
- PySide6
- Licensed local Spine installation
- Optional for `.rar`: 7-Zip, WinRAR, or unrar

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configure Spine

Copy the example config:

```powershell
copy config.example.json config.json
```

Edit `config.json` and set your local Spine path:

```json
{
  "spine_versions": {
    "3.7": "C:/Program Files/Spine/Spine.com",
    "3.8": "C:/Program Files/Spine/Spine.com",
    "4.0": "C:/Program Files/Spine/Spine.com",
    "4.1": "C:/Program Files/Spine/Spine.com",
    "4.2": "C:/Program Files/Spine/Spine.com"
  }
}
```

`Spine.com` is recommended for command-line use. In the desktop UI, choosing `Spine.exe` is also supported.

## Run Desktop UI

On Windows, the quickest way is to double-click:

```text
run_tool.bat
```

Or run manually:

```powershell
python main.py
```

Choose:

- Input type: folder or `.zip` / `.rar`
- Input path
- Spine executable
- Target Spine version

Output is created under:

```text
<input-folder>/SpineNewVersion/
```

Main output:

```text
SpineNewVersion/
  export/
  spine_new/
  export.zip
  spine_new.zip
```

## Input Example

```text
Boss_A/
  Boss_A.skel.bytes
  Boss_A.atlas.txt
  Boss_A.png
```

or:

```text
Boss_A/
  Boss_A.json
  Boss_A.atlas.txt
  Boss_A.png
```

## Run Headless CLI

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack
```

JSON export:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-json --pack
```

Fast export-only mode:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack --skip-spine-new
```

## Build

See [README_BUILD.md](README_BUILD.md).

Quick build:

```powershell
python -m pip install pyinstaller
build_windows.bat
```

Build output:

```text
dist/SpineUpgradePipelineTUN/
```

Spine executable and license files are never bundled.

## Contributing

Contributions are welcome.

Please:

- Do not include Spine executables or license files.
- Keep pipeline changes backward compatible.
- Test with a small sample project before opening a pull request.

## License

This project code is released under the MIT License. Spine is separate commercial software and is not included.
