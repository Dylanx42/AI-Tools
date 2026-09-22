$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name RackTool `
    --paths src `
    --collect-all racktool `
    scripts/windows_launcher.py

if (-not (Test-Path "dist/RackTool/RackTool.exe")) {
    throw "PyInstaller did not produce dist/RackTool/RackTool.exe"
}

Copy-Item "README.md" "dist/RackTool/README.md"
Copy-Item "scripts/windows-quick-start.txt" "dist/RackTool/使用说明.txt"

Write-Host "Windows portable build is ready: dist/RackTool/RackTool.exe"
