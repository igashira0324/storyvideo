#!/bin/bash

# Project Directory
PROJECT_ROOT="/home/nttdmse/aipf/RRMOTION/storyvideo"
VENV_DIR="$PROJECT_ROOT/venv"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install/Update requirements
echo "Checking dependencies..."
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"

# Run the generation script with all passed arguments
echo "Running generation pipeline..."
python3 "$PROJECT_ROOT/tools/generate_shots.py" "$@"

# Deactivate venv
deactivate
