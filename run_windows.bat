@echo off
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python run.py all
python -m pytest -q
start dashboard\index.html
