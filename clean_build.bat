@echo off
setlocal
cd /d "%~dp0"

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist SpineUpgradePipelineTUN.spec.bak del /q SpineUpgradePipelineTUN.spec.bak

echo Build artifacts cleaned.
endlocal
