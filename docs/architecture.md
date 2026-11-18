# Architecture and engineering decisions

## Logical layers, grains, and dependencies

| Layer | Asset | Grain / primary key | Notes |
|---|---|---|---|
| Bronze | `data/raw/customers.csv` | customer_id | Fictional demographics and income; intentionally injected bad records |
| Bronze | `data/raw/accounts.csv` | account_id | Products, credit limits, APR, origination month |
| Bronze | `data/raw/transactions.csv` | transaction_id | Signed cashflow events and category, linked to account |
| Bronze | `data/raw/servicing.csv` | (account_id, snapshot_month) | Month-end exposure, current DPD, payments |
| Silver | `dim_customer`, `dim_account` | customer_id, account_id | Validated reference entities |
| Silver | `fact_transaction` | transaction_id | Cleansed cashflow events |
| Silver | `fact_servicing` | (account_id, snapshot_month) | Month-end servicing outcomes |
| Assurance | `dq_checks`, `quarantine_events` | (source,rule) and event | Invalid source records rejected, checks retained |
| Feature | `v_month_cashflow` | (account_id, snapshot_month) | Cashflow per account month |
| Feature | `v_features` | (account_id, snapshot_month) | Trailing 3-month windows, lagged DPD, **future label** |
| Gold | `mart_portfolio_monthly` | snapshot_month | Executives' monthly book and arrears metrics |
| Gold | `mart_risk_segment` | (snapshot_month, product_type, region) | Risk segmentation and drilldowns |
| Gold | `mart_roll_rates` | (snapshot_month, from_bucket, to_bucket) | Delinquency transitions |
| Gold | `mart_vintage` | (origination_month, account_age_months, product_type) | Cohort deterioration |
| Gold | `mart_customer_360` | customer_id at latest portfolio month | Summary of exposure across linked accounts |
| Gold | `mart_spend_category` | (snapshot_month, category) | Household cashflow spend category |
| Model | `mart_model_scores` | (account_id, snapshot_month), held-out only | Strictly OOT probability and observed outcome |

`data/raw` = bronze; cleaned SQLite tables = silver; SQL views = gold. These are conceptual medallion layers, **not** a distributed lakehouse.

## Processing contract

1. Generate source rows from a documented RNG seed (default 42).
2. Apply schema, enum, uniqueness, numerical-range, date and referential checks in dependency order.
3. Log each failed rule and quarantine every offending source row (the same row may fail multiple rules).
4. Fail before publishing the warehouse if any source rejection rate exceeds 3% (tunable).
5. Rebuild silver tables from cleaned records. Enforce unique indexes.
6. Create read-only analytical SQL views; materialise only the model holdout scores.
7. Pick the better of a logistic model and a random forest on **validation months only**; retrain on train+validation and evaluate on untouched test months.
8. Persist the model, metrics, model card and standalone HTML dashboard.

## Why SQLite rather than a bigger stack?

- This project must be **runnable by an interviewer on a normal laptop** without credentials, Docker or paid services.
- SQLite supports advanced `LAG`, `LEAD`, rolling `SUM() OVER` windows and indexed relational joins.
- Python orchestrates deterministic stages, while SQL owns business definitions.
- Trade-off: not a demonstration of real-time streaming, cluster compute, Airflow orchestration or enterprise-scale concurrency. Those are explicit future extensions, not currently claimed features.

## Idempotency and trade-offs

`python run.py all --seed 42` produces the same synthetic data for the same customer/month settings. Warehouse rebuild is replace-all, rather than incremental; this is acceptable for a test-scale offline portfolio but is **not** a CDC-based production ingestion pattern. For a bank implementation, design an incremental watermark, backfill handling, SLA, operational job scheduler, data encryption, access controls, incident runbook, regulatory approvals and changes-management controls.

## Prediction and leakage boundary

At month-end `t`:
- Inputs: customer/account static metadata available at `t`, servicing at `t`, transactions up to `t`, trailing 3-month metrics, previous DPD.
- Label: `days_past_due(t+1) >= 30`, only when `days_past_due(t) < 30`.
- When no next month exists, target is **NULL**, not assumed to be no event.
- Training is based on older months; validation on the next 2; test on the final 3 labeled months. Time splits prevent training on *later* calendar events. Repeated accounts across months remain a realistic dependence caveat.
- Score table contains **historical held-out evaluations**; no claim of deployed, live operational predictions.

## Reconciliation

`SUM(mart_portfolio_monthly.accounts) == COUNT(fact_servicing)` across all months; `SUM(mart_portfolio_monthly.total_exposure_gbp) == SUM(fact_servicing.outstanding_balance_gbp)` with rounding caveat. This is asserted in tests. DQ anomalies are deliberately injected and must not enter silver.
