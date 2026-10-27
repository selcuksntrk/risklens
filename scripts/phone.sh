#!/usr/bin/env bash
# Test RiskLens on a phone: build the PWA, start the API, open a temporary HTTPS tunnel (the camera needs HTTPS).
# The printed https://*.trycloudflare.com URL is public while this runs; scans are capped per day/IP (see main.py).
set -euo pipefail
cd "$(dirname "$0")/.."
(cd frontend && npm run build >/dev/null)
(cd backend && uv run --env-file ../.env uvicorn app.main:app --host 127.0.0.1 --port 8000) &
API=$!
trap 'kill $API 2>/dev/null' EXIT
sleep 3
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000
