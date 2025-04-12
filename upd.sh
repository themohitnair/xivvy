#!/usr/bin/bash
set -euo pipefail

echo "Changing to script directory."
cd "$(dirname "$0")"
echo "Current directory: $(pwd)"

echo "Activating virtual environment."
source .venv/bin/activate
echo "Virtual environment activated."

echo "Running script.py..."
.venv/bin/python script.py

echo "Running startup.py..."
.venv/bin/python startup.py