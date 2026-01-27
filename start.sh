#!/usr/bin/env bash
set -euo pipefail

echo "PWD: $(pwd)"
echo "Listing root:"
ls -la

TARGET="$(find . -maxdepth 4 -name main.py -print | head -n 1)"

if [[ -z "${TARGET}" ]]; then
  echo "ERROR: main.py not found within 4 levels."
  exit 1
fi

echo "Running: python ${TARGET}"
python "${TARGET}"
