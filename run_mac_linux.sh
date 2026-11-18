#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py all
python -m pytest -q
python -m webbrowser dashboard/index.html
