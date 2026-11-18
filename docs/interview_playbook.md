# BankPulse: senior banking data analyst / analytics engineer interview playbook

## Five-minute live demo

1. Open `demo/sample_dashboard.html` or locally generated `dashboard/index.html` in a browser. Explain that every observation is synthetic.
2. Ask a business question: “Which product and region is contributing most to 30+ DPD by account count? Is the exposure-weighted picture different?” Show segment/portfolio view.
3. Walk through `sql/01_analytics_marts.sql`. Highlight source grain, `LAG`, `LEAD`, `ROWS BETWEEN 2 PRECEDING`, roll rate calculation, and account-vs-balance weighting.
4. Show `src/bankpulse/pipeline.py`, where quality rules quarantine duplicate and orphan records. Show `reports/data_quality.json` (or `demo/data_quality_sample.json`).
5. Show `reports/MODEL_CARD.md` (or `demo/model_card_sample.md`), explain model selection on validation months, untouched holdout and why next-month DPD is only a label.
6. Show `tests/` and `.github/workflows/ci.yml` to prove a fresh run is reproducible.

## Interview Q&A with defensible answers

**Q: Why this architecture?** SQLite is free, fast and easy for reviewers to run, but still allows relational design and advanced window SQL. A real bank version would move transformations to an approved warehouse/lakehouse, integrate orchestration, security, monitoring and approvals.

**Q: Explain the business problem.** Risk MI needs timely portfolio exposure, migration and delinquency metrics, while collections triage wants an interpretable, forward-looking flag identifying currently non-30+ accounts that might roll into 30+ next month.

**Q: What is the grain?** Servicing: account at calendar month; transaction: transaction ID; account: one account; customer: one customer. This prevents naive double-counting when joining transactions to month-end balances.

**Q: What does 30+ DPD mean?** Days past due at month-end >=30; the project's 30+ rate is account-weighted. The target is **first observed transition** from <30 at month t to >=30 at month t+1, not probability of default as defined by bank capital models.

**Q: Is the model leakage-safe?** Current and historical inputs only, supervised label created with `LEAD`, excluded from FEATURES, training and validation before held-out test months. Remaining risk: correlated samples from the same accounts over time, simulator misspecification and any real-world record lag.

**Q: What happens if quality checks fail?** Each failure is recorded; invalid rows quarantine. A per-source invalid rate over the threshold aborts the warehouse build (fail closed) before publishing tables. Production would send alerts and support manual review.

**Q: Why not choose by held-out accuracy?** The two candidates are compared on validation-month ROC AUC. After choosing, we refit on development data and assess once on held-out months. Test labels do not select the algorithm.

**Q: How do you explain trade-offs to executives?** Delinquency percent is count-weighted and may differ from balance-weighted exposure; PSI is illustrative drift monitoring; score-based alerts imply workload and false positives. Synthetic evidence cannot guide actual decisions.

**Q: Which improvements would you implement first?** Add contractual data freshness and completeness, incremental ingest, a true change-log, an orchestrator with retries and SLAs, missing-period tests, dbt schema contracts, security policies, historic restatement, compliance review, confidence intervals, calibration and decision impact monitoring.

**Q: What data would you request from business stakeholders?** Source-system ownership, account servicing event timing, payment holidays/forbearance, charge-offs, cures, DPD policy rules, as-of cutoff, leakage controls, legal basis, retention, anonymisation, quality thresholds and target use cases.

**Q: Which SQL tools are showcased?** Multi-table joins, filters, conditional aggregation, window functions (`LEAD`, `LAG`, partitioned trailing sums), cohort analysis, percent/denominator definitions, null handling and indexes.

## CV / LinkedIn bullet suggestion — edit to reflect what you personally implemented

> Built and evaluated a local-first **synthetic retail banking risk intelligence platform** using Python, SQL, pandas and scikit-learn, integrating source ingestion, automated data-quality quarantine, customer/account analytics marts, temporal model validation, and interactive portfolio reporting; added pytest and GitHub Actions CI.

**Avoid claiming:** real-world model deployment, regulatory approval, production banking data, achieved commercial lift, continuous live monitoring, or a particular AUC across all runs. All data and scores are simulated, and this repository is an AI-assisted starting point for your own development.

## Suggested extensions to demonstrate independent expertise

- Add a true incremental refresh and late-arriving historical corrections, with regression tests.
- Compare SQL query plans before/after indexes on larger synthetic volumes; publish timings.
- Port silver/gold to DuckDB+Parquet or dbt and compare developer experience.
- Add synthetic SME credit exposure, an IFRS 9 staging *illustration* (explicitly not compliant) or a BCBS 239 control matrix.
- Implement training-time model registry, calibration and cost-sensitive alert optimisation.
- Publish your own 3-page written analytics insight with segment recommendations and caveats.
