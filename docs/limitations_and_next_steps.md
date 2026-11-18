# Current limitations, safety and road map

## What works now

Deterministic fictional data; source validation, rejected-record logging and configurable fail-closed thresholds; validated and indexed SQLite relational warehouse; SQL reporting views; logistic-vs-random-forest model selection; temporal train/validation/test; repeatable command-line interface; offline Plotly dashboard; optional Streamlit app; regression and integration tests in GitHub Actions.

## What is deliberately NOT claimed

- No real banking, credit bureau or customer data and no production use.
- No guarantee or empirical validation of AUC, credit outcomes, customer fairness or stability beyond the simulator.
- Not probability-of-default (PD) estimation under IRB, not IFRS 9 staging and not compliant with BCBS 239.
- No formal regulatory model review, audit sign-off, immutable event store, RBAC, encryption at rest, privacy impact assessment, explainability framework or bias certification.
- No true continuously scheduled orchestration, streaming transactions, Spark jobs, dbt deployment, CDC or scalable cloud lakehouse.
- The synthetic 'linked cashflow' transactions are a simplified behavioural proxy, not a balanced banking general ledger.
- Some source quality checks validate shape and domain, not cross-source timeliness or completeness. Rebuilt warehouse does not enforce transactional CDC semantics.
- The optional Streamlit app may need installing separately. Offline HTML is fully standalone.

## Roadmap for high-tier financial-services interviews

### Phase 1: Trust, observability and analytical rigor
- Add monthly completeness checks, source freshness timestamps and reporting SLAs.
- Introduce expected-vs-actual DQ controls with owner, tolerance and severity metadata.
- Implement reconciliation of transaction events to an independent ledger fixture.
- Add account age cohort visualisations and BI measure reconciliation tests.

### Phase 2: Enterprise data engineering
- Introduce DuckDB or Snowflake with Parquet partitions and benchmark vs SQLite.
- Use dbt staging/intermediate/marts, schema contracts and documentation pages.
- Orchestrate with Airflow/Dagster/Prefect; add explicit retries, backfills and data lineage capture.
- Enforce immutable bronze storage and incremental changes/upserts.

### Phase 3: Model risk management
- Add interval-aware validation, calibration curves, bootstrapped uncertainty, segment performance and fairness audits.
- Exclude recent interventions/collections outcomes that could lead to intervention bias.
- Record feature materialisation timestamps; monitor training/serving skew and alert volumes.
- Test cost-sensitive triage with approved business constraints and champion/challenger governance.

### Phase 4: Production controls
- Least privilege, pseudonymisation, secret management, encryption, retention and access audits.
- Incident handling, job SLOs, cost optimisation, business sign-offs and approved change management.

## Verification boundary

The complete core CLI and tests were executed in the packaging environment. The optional Streamlit app is included as a runnable extension; it requires a separate install because the build environment does not have Streamlit available. All results depend on the user's Python package versions and platform.
