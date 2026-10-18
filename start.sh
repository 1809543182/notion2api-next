#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "Install Python 3.11+ first."; exit 1; }
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
if [ ! -x .venv/bin/python ]; then "$PY" -m venv .venv; fi
PY="$PWD/.venv/bin/python"
"$PY" -m pip install -r requirements.txt -c constraints.txt
if [ ! -f .env ]; then cp .env.example .env; chmod 600 .env; fi
if [ ! -f accounts.json ]; then "$PY" login.py --timeout 900; fi
echo "Web UI: http://127.0.0.1:8000 (Ctrl+C to stop)"
exec "$PY" -m uvicorn app.server:app --host 127.0.0.1 --port 8000
