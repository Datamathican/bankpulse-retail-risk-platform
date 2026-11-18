# Verification notes — packaging run (18 November 2026)

In the build environment, the full default command `python run.py all --customers 1200 --months 30` completed without error. All eight `pytest` checks passed in an earlier integration run.

## Default output observed

- Source generated: 1,200 fictional customers, 1,482 raw accounts, 210,580 raw cashflow transactions, and 35,020 raw servicing snapshots.
- After data quality: 1,200 clean customers, 1,480 accounts, 210,578 transactions, and 35,018 monthly snapshots.
- Nine failed rule events, eight distinct rejected source records; no real bank/customer data.
- Model selection: logistic regression chosen on validation periods.
- Holdout: March–May 2026, 3,677 observations; ROC AUC approximately **0.643** and average precision approximately **0.156**.
- Generated offline dashboard, scored holdout rows, JSON metrics and model card.

**Interpretation:** these are **synthetic simulator-generated results**, not independent evidence that the model generalises to real bank accounts. Small demo results differ from full-run results. Reported classification scores and incident rates will change if the simulator seed or date coverage changes.

## Testing commands

```bash
python -m pytest -q
python run.py all --customers 250 --months 16
python scripts/run_example_queries.py
```

GitHub Actions repeats testing on Ubuntu with Python 3.11 and 3.13 using `.github/workflows/ci.yml`. Its status is not known until published to your GitHub account. Optional Streamlit application requires its own installation; it is not exercised by the standard pytest suite.
