#!/usr/bin/bash
set -euo pipefail

echo "Changing to script directory."
cd "$(dirname "$0")"
echo "Current directory: $(pwd)"

rm -rf last_paper_processed.txt
rm -rf if_old_papers_processed.txt

echo "Activating virtual environment."
source .venv/bin/activate
echo "Virtual environment activated."

echo "Running script.py..."
.venv/bin/python script.py

echo "Running startup.py..."
.venv/bin/python startup.py