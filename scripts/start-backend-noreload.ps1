$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not $env:MANUAL_RATING_SESSION_SECRET) {
  $env:MANUAL_RATING_SESSION_SECRET = "manual-rating-dev-secret"
}
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
