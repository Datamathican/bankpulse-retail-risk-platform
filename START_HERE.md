# Start here — 3 things to try

**1. Look at the dashboard without installing anything.** Double-click `demo/sample_dashboard.html`.

**2. Run the full project.** In Terminal (Mac) or PowerShell (Windows), in this folder:

```bash
python -m venv .venv
# Mac: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py all --customers 250 --months 16
python -m pytest -q
```

Double-click `dashboard/index.html` for the version generated on your computer.

**3. Upload using GitHub Desktop.** Extract this archive → open GitHub Desktop → File → Add local repository → select the project folder → if prompted, choose Create Repository Here → commit the files → Publish repository. Open GitHub → Actions to watch the tests run. Read README.md for the full directions.

**Important:** Everything is synthetic, and the project is an AI-assisted starting point. Read and adapt it before interview use. Do not upload real bank/customer information.
