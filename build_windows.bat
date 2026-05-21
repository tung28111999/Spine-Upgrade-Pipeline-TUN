@echo off
setlocal
cd /d "%~dp0"

python -m PyInstaller SpineUpgradePipelineTUN.spec
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Build complete: dist\SpineUpgradePipelineTUN
endlocal
