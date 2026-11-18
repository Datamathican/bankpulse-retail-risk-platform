-- BankPulse SQL analytical layer (SQLite 3.35+). All monetary amounts are fictional GBP.
-- Definitions: current DPD is known at month-end; next_month_30dpd is strictly a future label.

CREATE VIEW v_month_cashflow AS
SELECT account_id, SUBSTR(transaction_date,1,7) AS snapshot_month,
       ROUND(SUM(CASE WHEN amount_gbp > 0 THEN amount_gbp ELSE 0 END),2) AS inflow_gbp,
       ROUND(SUM(CASE WHEN amount_gbp < 0 THEN -amount_gbp ELSE 0 END),2) AS outflow_gbp,
       SUM(CASE WHEN category = 'Returned Payment' THEN 1 ELSE 0 END) AS returned_payments
FROM fact_transaction
GROUP BY account_id, SUBSTR(transaction_date,1,7);

CREATE VIEW v_features AS
WITH features AS (
  SELECT s.account_id, a.customer_id, s.snapshot_month,
         a.product_type, c.region, c.employment_type, c.age_band,
         c.monthly_income_gbp, a.credit_limit_gbp, a.apr, a.origination_month,
         s.outstanding_balance_gbp, s.days_past_due,
         ROUND(CAST(s.outstanding_balance_gbp AS REAL)/NULLIF(a.credit_limit_gbp,0),4) AS utilisation,
         ROUND(CAST(s.payment_received_gbp AS REAL)/NULLIF(s.minimum_payment_gbp,0),4) AS payment_ratio,
         COALESCE(m.inflow_gbp,0) AS monthly_inflow_gbp,
         COALESCE(m.outflow_gbp,0) AS monthly_outflow_gbp,
         SUM(COALESCE(m.inflow_gbp,0)) OVER (PARTITION BY s.account_id ORDER BY s.snapshot_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS inflow_3m_gbp,
         SUM(COALESCE(m.outflow_gbp,0)) OVER (PARTITION BY s.account_id ORDER BY s.snapshot_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS outflow_3m_gbp,
         SUM(COALESCE(m.returned_payments,0)) OVER (PARTITION BY s.account_id ORDER BY s.snapshot_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS returned_payments_3m,
         SUM(CASE WHEN s.days_past_due > 0 THEN 1 ELSE 0 END) OVER (PARTITION BY s.account_id ORDER BY s.snapshot_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS late_count_3m,
         COALESCE(LAG(s.days_past_due) OVER (PARTITION BY s.account_id ORDER BY s.snapshot_month),0) AS previous_dpd,
         LEAD(s.days_past_due) OVER (PARTITION BY s.account_id ORDER BY s.snapshot_month) AS next_month_dpd,
         ((CAST(SUBSTR(s.snapshot_month,1,4) AS INTEGER)-CAST(SUBSTR(a.origination_month,1,4) AS INTEGER))*12+
          (CAST(SUBSTR(s.snapshot_month,6,2) AS INTEGER)-CAST(SUBSTR(a.origination_month,6,2) AS INTEGER))) AS account_age_months
  FROM fact_servicing s
  JOIN dim_account a ON a.account_id = s.account_id
  JOIN dim_customer c ON c.customer_id = a.customer_id
  LEFT JOIN v_month_cashflow m ON m.account_id=s.account_id AND m.snapshot_month=s.snapshot_month
)
SELECT features.*,
       CASE WHEN next_month_dpd IS NULL OR days_past_due>=30 THEN NULL
            WHEN next_month_dpd>=30 THEN 1 ELSE 0 END AS target_next_30dpd
FROM features;

-- Executives: balance, current arrears and month-ahead observed transitions.
CREATE VIEW mart_portfolio_monthly AS
SELECT snapshot_month,
       COUNT(*) AS accounts,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(SUM(outstanding_balance_gbp),2) AS total_exposure_gbp,
       ROUND(SUM(CASE WHEN days_past_due>=30 THEN outstanding_balance_gbp ELSE 0 END),2) AS balance_30plus_gbp,
       SUM(CASE WHEN days_past_due>=30 THEN 1 ELSE 0 END) AS accounts_30plus,
       ROUND(100.0*SUM(CASE WHEN days_past_due>=30 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),2) AS pct_accounts_30plus,
       SUM(CASE WHEN target_next_30dpd IS NOT NULL THEN 1 ELSE 0 END) AS labelled_active_accounts,
       SUM(CASE WHEN target_next_30dpd=1 THEN 1 ELSE 0 END) AS next_month_new_30plus_accounts
FROM v_features GROUP BY snapshot_month ORDER BY snapshot_month;

-- Business slice: compare risk concentrations by region and product.
CREATE VIEW mart_risk_segment AS
SELECT snapshot_month, product_type, region,
       COUNT(*) AS accounts,
       ROUND(SUM(outstanding_balance_gbp),2) AS exposure_gbp,
       SUM(CASE WHEN days_past_due>=30 THEN 1 ELSE 0 END) AS accounts_30plus,
       ROUND(100.0*SUM(CASE WHEN days_past_due>=30 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),2) AS pct_accounts_30plus,
       ROUND(AVG(utilisation),3) AS average_utilisation
FROM v_features GROUP BY snapshot_month,product_type,region;

-- Roll rates: what proportion of accounts migrate between delinquency buckets?
CREATE VIEW mart_roll_rates AS
WITH bucketed AS (
 SELECT account_id, snapshot_month, outstanding_balance_gbp,
        CASE WHEN days_past_due=0 THEN 'Current' WHEN days_past_due<30 THEN '1-29' WHEN days_past_due<60 THEN '30-59' ELSE '60+' END AS to_bucket,
        LAG(CASE WHEN days_past_due=0 THEN 'Current' WHEN days_past_due<30 THEN '1-29' WHEN days_past_due<60 THEN '30-59' ELSE '60+' END)
          OVER (PARTITION BY account_id ORDER BY snapshot_month) AS from_bucket
 FROM fact_servicing
)
SELECT snapshot_month,from_bucket,to_bucket,COUNT(*) AS accounts,
       ROUND(SUM(outstanding_balance_gbp),2) AS ending_exposure_gbp,
       ROUND(100.0*COUNT(*)/NULLIF(SUM(COUNT(*)) OVER (PARTITION BY snapshot_month,from_bucket),0),2) AS roll_rate_pct
FROM bucketed WHERE from_bucket IS NOT NULL
GROUP BY snapshot_month,from_bucket,to_bucket;

-- Vintage analysis: ageing of each original lending cohort.
CREATE VIEW mart_vintage AS
SELECT origination_month,account_age_months,product_type,COUNT(*) AS accounts,
       ROUND(SUM(outstanding_balance_gbp),2) AS exposure_gbp,
       ROUND(100.0*SUM(CASE WHEN days_past_due>=30 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),2) AS pct_30plus
FROM v_features
GROUP BY origination_month,account_age_months,product_type;

CREATE VIEW mart_customer_360 AS
WITH latest AS (SELECT MAX(snapshot_month) AS snapshot_month FROM fact_servicing)
SELECT f.customer_id, f.region,COUNT(*) AS account_count,
       ROUND(SUM(f.outstanding_balance_gbp),2) AS outstanding_exposure_gbp,
       ROUND(AVG(f.utilisation),3) AS average_utilisation,
       MAX(f.days_past_due) AS max_days_past_due,
       SUM(CASE WHEN f.days_past_due>=30 THEN 1 ELSE 0 END) AS delinquent_accounts
FROM v_features f JOIN latest l ON f.snapshot_month=l.snapshot_month
GROUP BY f.customer_id,f.region;

CREATE VIEW mart_spend_category AS
SELECT SUBSTR(transaction_date,1,7) AS snapshot_month,category,
       COUNT(*) AS transaction_count,
       ROUND(SUM(CASE WHEN amount_gbp<0 THEN -amount_gbp ELSE 0 END),2) AS spend_gbp
FROM fact_transaction GROUP BY SUBSTR(transaction_date,1,7),category;
