#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
  echo "Python executable not found or not executable: $PYTHON" >&2
  exit 1
fi

echo "==> Ruff"
"$PYTHON" -m ruff check src tests

echo "==> Tests and coverage"
"$PYTHON" -m pytest

echo "==> Dependency consistency"
"$PYTHON" -m pip check

echo "==> Dependency vulnerability audit"
"$PYTHON" -m pip_audit

echo "==> Package build"
"$PYTHON" -m pip wheel --no-deps --wheel-dir dist .

echo "All verification checks passed."

