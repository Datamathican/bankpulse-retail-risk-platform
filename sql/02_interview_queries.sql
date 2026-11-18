-- Query A: last 6 months, portfolio deterioration and exposure concentration.
SELECT snapshot_month,accounts,total_exposure_gbp,pct_accounts_30plus,
       LAG(pct_accounts_30plus) OVER (ORDER BY snapshot_month) AS prior_month_pct,
       ROUND(pct_accounts_30plus-LAG(pct_accounts_30plus) OVER (ORDER BY snapshot_month),2) AS mom_change_pp
FROM mart_portfolio_monthly ORDER BY snapshot_month DESC LIMIT 6;

-- Query B: high-risk segments in the latest month, minimum credible denominator.
SELECT product_type,region,accounts,accounts_30plus,pct_accounts_30plus,exposure_gbp
FROM mart_risk_segment WHERE snapshot_month=(SELECT MAX(snapshot_month) FROM fact_servicing)
  AND accounts>=15
ORDER BY pct_accounts_30plus DESC,exposure_gbp DESC LIMIT 15;

-- Query C: collection roll-rate from current to any 30+ DPD bucket.
SELECT snapshot_month,
       SUM(CASE WHEN to_bucket IN ('30-59','60+') THEN accounts ELSE 0 END) AS current_to_30plus,
       SUM(accounts) AS previously_current,
       ROUND(100.0*SUM(CASE WHEN to_bucket IN ('30-59','60+') THEN accounts ELSE 0 END)/NULLIF(SUM(accounts),0),2) AS pct_current_to_30plus
FROM mart_roll_rates WHERE from_bucket='Current'
GROUP BY snapshot_month ORDER BY snapshot_month;

-- Query D: the largest recent cohorts and their most recent observed arrears.
WITH scored AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY origination_month,product_type ORDER BY account_age_months DESC) AS n
 FROM mart_vintage
)
SELECT origination_month,product_type,account_age_months,accounts,pct_30plus
FROM scored WHERE n=1 ORDER BY origination_month DESC,accounts DESC LIMIT 15;

-- Query E: observed alert performance by selected segment on strict holdout.
SELECT product_type,COUNT(*) AS tested_accounts,
       SUM(risk_alert) AS alerts,
       SUM(CASE WHEN risk_alert=1 AND target_next_30dpd=1 THEN 1 ELSE 0 END) AS true_positive_alerts,
       ROUND(100.0*SUM(CASE WHEN risk_alert=1 AND target_next_30dpd=1 THEN 1 ELSE 0 END)/NULLIF(SUM(risk_alert),0),2) AS alert_precision_pct
FROM mart_model_scores GROUP BY product_type ORDER BY tested_accounts DESC;

-- Query F: reconcile source-level servicing to the aggregate financial view.
SELECT ROUND((SELECT SUM(outstanding_balance_gbp) FROM fact_servicing),2) AS silver_exposure_gbp,
       ROUND((SELECT SUM(total_exposure_gbp) FROM mart_portfolio_monthly),2) AS gold_exposure_gbp,
       (SELECT COUNT(*) FROM fact_servicing) AS silver_account_months,
       (SELECT SUM(accounts) FROM mart_portfolio_monthly) AS gold_account_months;
