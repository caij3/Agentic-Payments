#!/usr/bin/env bash
# Start the hosted demo from this laptop: the app (presenter-locked, live Qatom) plus the Cloudflare
# tunnel to demo.chud.ing. Keeps the Mac awake while running. Ctrl-C stops both.
#
#   ./scripts/start_live.sh            # live Qatom rail
#   RAIL=mock ./scripts/start_live.sh  # practice rail, if Qatom misbehaves
#
# Needs: .venv set up, .env with PRESENTER_KEY (and ANTHROPIC_API_KEY for Claude), cloudflared logged in
# on this Mac with the "scamguard" tunnel (cloudflared tunnel list).
set -euo pipefail
cd "$(dirname "$0")/.."

if lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Something is already running on port 8000. Stop it first (or it's already live)."
  exit 1
fi

HOSTED=1 RAIL="${RAIL:-qatom}" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  curl -s -o /dev/null http://127.0.0.1:8000/ && break
  sleep 0.5
done
echo "App is up on http://127.0.0.1:8000 (rail: ${RAIL:-qatom}). Opening the tunnel to https://demo.chud.ing ..."
caffeinate -i cloudflared tunnel run --url http://127.0.0.1:8000 scamguard
