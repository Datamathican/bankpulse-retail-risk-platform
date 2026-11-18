# Business glossary and data dictionary

**Dataset classification:** wholly fictional records and identifiers. Monetary units GBP. Each snapshot is a calendar month ending observation represented as `YYYY-MM`.

| Field / metric | Definition, owner, and control |
|---|---|
| `customer_id` | Fictional stable customer key; source `customers`; must be unique and nonempty. |
| `account_id` | Fictional account key; exactly one customer via `dim_account.customer_id`. |
| `product_type` | `Credit Card`, `Personal Loan` or `Overdraft`; consistent enumerated domain. |
| `credit_limit_gbp` | Simulated account facility/initial lending limit. Positive. Not committed exposure EAD. |
| `monthly_income_gbp` | Simulated monthly household income. Used as illustration, not affordability verified by bank. |
| `transaction_date` | Simulated calendar date of a cashflow event. |
| `category` | Simplified cashflow category; `Income` positive and outflows negative. Not bank GL transaction coding. |
| `amount_gbp` | Signed event amount; positive=inflow, negative=outflow. |
| `snapshot_month` | Month-end observational period, not actual processing timestamp. |
| `outstanding_balance_gbp` | Fictional month-end principal-like amount. Summed to calculate outstanding exposure. |
| `days_past_due` | Recorded month-end arrears days; values 0, 5, 15, 30, 60 or 90 in simulator. |
| `minimum_payment_gbp` | Simulated minimum required payment for month. |
| `payment_received_gbp` | Simulated amount paid. `payment_ratio` = received / minimum. |
| `utilisation` | Outstanding balance / credit limit, 0–1.25 permitted after source quality checks. |
| `inflow_3m_gbp` | Trailing 3 available monthly inflow sums, including snapshot month; early histories contain fewer than 3 observations. |
| `outflow_3m_gbp` | Trailing 3 available monthly outflow sums, including snapshot month. |
| `returned_payments_3m` | Count of `Returned Payment` cashflow events in trailing 3 observed months. |
| `late_count_3m` | Count of months with any observed DPD in last 3 snapshots. |
| `previous_dpd` | Lagged previous recorded month's DPD; 0 if no prior snapshot. |
| `account_age_months` | Whole calendar month difference between snapshot month and origination month. |
| `accounts_30plus` | Count of accounts whose current DPD >=30. |
| `pct_accounts_30plus` | `100 × accounts_30plus / active accounts` within a selected month or segment. It is account-weighted, not exposure-weighted. |
| `balance_30plus_gbp` | Sum of outstanding balance for accounts currently >=30 DPD. |
| `target_next_30dpd` | **Future label**. For accounts <30 DPD now: 1 if next month DPD >=30; 0 if next month <30; NULL otherwise. |
| `roll_rate_pct` | Among accounts with given last-month DPD bucket, share that transitioned into the stated current bucket. |
| `risk_score` | Estimated probability of a first transition to >=30 DPD next month; assessed on synthetic held-out months only. |
| `risk_alert` | Historical operational triage flag set at top-decile validation threshold; not an automated banking decision. |

## Example critical data elements and owners (hypothetical)

| KDE | Hypothetical business steward | Control |
|---|---|---|
| `account_id` | Banking operations | Unique/required, valid relationship |
| `snapshot_month` | Servicing MI owner | One monthly record per account |
| `outstanding_balance_gbp` | Finance / Risk MI | Numeric and within synthetic facility boundary |
| `days_past_due` | Collections operations | Nonnegative, integer, domain 0–180 |
| `product_type` | Product Data Owner | Controlled product taxonomy |
| `monthly_income_gbp` | Customer Data Owner | Non-null, positive; does not imply verified income |

**Lineage:** See `docs/lineage.json` for machine-readable asset dependencies. This is illustrative and not regulatory certification or BCBS 239 compliance.
