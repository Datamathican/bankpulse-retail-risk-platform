# Portfolio project research (18 November 2026)

These are **examples of what public builders and employers discuss**, not a scientifically ranked 'most trending' leaderboard. GitHub star counts change and do not establish hiring success.

## Sample repositories and observed themes

| Public resource | What it demonstrates / why it informed this project |
|---|---|
| [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | End-to-end learning around pipelines, SQL, transformations and deployment concepts |
| [calemccammon/data-engineer-finance-analytics](https://github.com/calemccammon/data-engineer-finance-analytics) | Finance-oriented ELT using DuckDB, dbt, orchestration and BI |
| [pavelszr/sql-analytics-portfolio](https://github.com/pavelszr/sql-analytics-portfolio) | Senior-level SQL using retail banking data and loan delinquency queries |
| [battina1999/airline-data-platform](https://github.com/battina1999/airline-data-platform) | Tests, ETL, data quality, data marts and ML evaluation across an end-to-end portfolio |
| [phaiffer/data-engineering-portfolio](https://github.com/phaiffer/data-engineering-portfolio) | Modular analytics and SQL engineering examples |
| [sophie-nguyenthuthuy/practical-data-engineering-2026](https://github.com/sophie-nguyenthuthuy/practical-data-engineering-2026) | Modern laptop-scale analytics stacks and observability |

## Relevant skill demand examples

- [Rothstein Recruitment: Banking Data Engineer](https://uk.linkedin.com/jobs/view/data-engineer-python-sql-airflow-dbt-banking-at-rothstein-recruitment-4417046623): Python, SQL, Airflow, dbt and regulated bank controls.
- [UK senior risk data engineer example](https://www.jobsitejobs.co.uk/job/14934554/senior-data-engineer-python-databricks-counterparty-credit-risk/): Python, PySpark, SQL, lakehouses and credit risk.
- [Ebury credit risk and underwriting analyst role](https://builtin.com/job/data-analyst-credit-risk-underwriting/8804995): advanced SQL/Python, analytical data models and reproducibility. Link represents a role example and may no longer accept applications.
- [British Business Bank senior credit risk job description](https://www.british-business-bank.co.uk/sites/g/files/sovrnj166/files/2025-07/Senior%20Credit%20Risk%20JD%20-%20202507%20.pdf): reporting, data quality, Python and credit portfolio analytics.

## Design response

1. A banking-specific use case demonstrates relevant domain judgement.
2. Analytical SQL and working data quality are more defensible than a notebook-only portfolio.
3. A time-based held-out ML evaluation answers basic model governance questions.
4. A no-cloud local demonstration makes an interview live demo practical.
5. This implementation uses SQLite rather than claiming a dbt/Airflow stack that is not implemented. Future upgrade paths are documented without exaggeration.

All code in this starter project was generated for this deliverable rather than copied from the linked repositories.
