#!/usr/bin/env bash
set -euo pipefail

echo "========== BOT START =========="
echo "Working dir: $(pwd)"
echo "ENV: ${ENV:-dev}"
python --version
echo "==============================="

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

if [[ ! -f "./main.py" ]]; then
  echo "ERROR: main.py not found in root."
  ls -la
  exit 1
fi

exec python main.py
