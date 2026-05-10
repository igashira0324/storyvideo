#!/bin/bash
set -euo pipefail
set -e

# Project Directory
# Get the directory where the script is located
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_ROOT/venv"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install/Update requirements with proxy bypass
echo "Checking dependencies (Bypassing proxy)..."
env -u http_proxy -u https_proxy pip install --upgrade pip
env -u http_proxy -u https_proxy pip install -r "$PROJECT_ROOT/requirements.txt"

# Run the generation script with all passed arguments (Bypassing proxy)
echo "Running generation pipeline..."
env -u http_proxy -u https_proxy python3 "$PROJECT_ROOT/tools/generate_shots.py" "$@"

# Deactivate venv
deactivate
