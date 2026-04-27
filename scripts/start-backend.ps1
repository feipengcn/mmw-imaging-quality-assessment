$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
