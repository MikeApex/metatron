#!/usr/bin/env bash
# One-time setup: creates a Python 3.12 venv and installs Kokoro + deps.
# Run from anywhere — it always installs relative to this script's directory.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/venv"
PYTHON=/opt/homebrew/bin/python3.12

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: python3.12 not found at $PYTHON"
    echo "Run: brew install python@3.12"
    exit 1
fi

echo "Creating venv at $VENV ..."
"$PYTHON" -m venv "$VENV"

echo "Installing kokoro, torch, soundfile ..."
"$VENV/bin/pip" install --upgrade pip -q
"$VENV/bin/pip" install kokoro soundfile torch

echo ""
echo "Done. Test with:"
echo "  echo 'Hello, this is Kokoro.' | $VENV/bin/python $SCRIPT_DIR/speak.py"
