# Model card — BankPulse month-ahead delinquency early warning

**This is a research demonstration trained entirely on artificially generated data. Not for customer decisions.**

## Intended prediction
Predict first transition to >=30 days past due in the following calendar month; only score accounts currently <30 DPD.

## Dataset and validation
- Train: 2024-01 to 2024-10 (1,833 rows)
- Validation: 2024-11 to 2024-12 (539 rows)
- Strict held-out test: 2025-01 to 2025-03 (782 rows)
- No random row splitting: accounts can appear in multiple months, so time-wise holdout is essential.
- Label is next month's observed >=30 DPD; last month has no target and is never used for training.

## Model selection (validation only)
- Logistic regression validation ROC AUC: 0.637
- Random forest validation ROC AUC: 0.637
- Selected: **random_forest**; refitted on train + validation, tested once.
- Alert cutoff: validation upper decile of scores = **0.168** (operational triage demonstration).

## Held-out performance
- ROC AUC: **0.590**
- Average precision: **0.100**
- Brier score: **0.069**
- Top-decile event capture: **15.8%**
- High-risk alert precision: **13.1%**
- High-risk alert recall: **31.6%**
- Utilisation PSI (development vs test): **0.145** (illustrative; should be tracked over time).

## Governance and limitations
- Entirely synthetic, so AUC values reflect the simulator's assumptions, not bank evidence.
- No individual automated decisions; not approved for lending, arrears treatment, regulatory capital or impairment.
- Sensitive or protected attributes are not direct features; a real deployment needs formal fairness testing, explainability and customer outcomes review.
- Current-period servicing and trailing three-month cashflow are features; future DPD is label only.
- Observe performance, calibration and selection bias on representative production data before any use.
- Analysts must validate the account grain, 30-day definition, observation timestamp and treatment of missing months.
