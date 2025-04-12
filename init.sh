#!/usr/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

echo "Creating virtual environment using uv."
/usr/bin/uv venv --python=3.13

echo "Activating virtual environment."
source .venv/bin/activate

echo "Installing dependencies from requirements.txt."
/usr/bin/uv pip install -r requirements.txt

echo "Your environment is ready to cook!"