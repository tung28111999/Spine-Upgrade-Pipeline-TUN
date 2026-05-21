# Headless Runner

Run the Spine Upgrade Pipeline TUN from command line without opening the PySide6 UI.

## Setup

Edit `config.json` and set each `spine_versions` entry to the local Spine launcher path, usually:

```json
"4.1": "C:/Program Files/Spine/Spine.exe"
```

`default_old_version` may be `"auto"` so the runner detects the source version from the skeleton file.

## Examples

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --old 3.8 --new 4.1 --export-json --pack
```

Auto-detect old/source Spine version and export binary:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack
```

Skip atlas packing:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --no-pack
```

Dev fast mode, skip creating upgraded `.spine` project:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack --skip-spine-new
```

Verbose logs:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --verbose
```

Keep only the final deliverable folders after success:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack --final-only
```

Create final archives as RAR instead of ZIP:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --archive-format rar
```

## Output

The runner creates:

- `output/source`
- `output/images`
- `output/spine_old`
- `output/spine_new` unless `--skip-spine-new` is used
- `output/export`

Successful runs also create:

- `output/spine_new.zip` and `output/export.zip`
- or `.rar` files when `--archive-format rar` is used and RAR creation is available
- `output/logs/process.log`
- `output/logs/errors.log`
- `output/summary.json`

With `--skip-spine-new`, the runner skips creating/naming/nesting the upgraded `.spine` project and only archives `export` plus any `same_version` assets.

With `--final-only`, successful runs keep only:

- `output/spine_new`
- `output/export`

Original input files are never modified.

If multiple skeleton jobs are found, the runner processes all of them. Each job writes to a separate subfolder under `spine_new` and `export`.

## Exit Codes

- `0` success
- `1` validation error
- `2` pipeline failed
- `3` Spine CLI failed
- `4` unexpected error
