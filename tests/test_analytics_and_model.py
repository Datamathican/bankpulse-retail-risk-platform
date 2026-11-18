import json
import sqlite3
import pandas as pd
from bankpulse.model import FEATURES, chronological_splits


def test_sql_marts_reconcile_to_source(pipeline_output):
    root,_,_,_=pipeline_output
    with sqlite3.connect(root/"warehouse"/"bankpulse.sqlite") as con:
        source=con.execute("SELECT COUNT(*),ROUND(SUM(outstanding_balance_gbp),2) FROM fact_servicing").fetchone()
        marts=con.execute("SELECT SUM(accounts),ROUND(SUM(total_exposure_gbp),2) FROM mart_portfolio_monthly").fetchone()
        assert source==marts
        assert con.execute("SELECT COUNT(*) FROM mart_risk_segment").fetchone()[0]>10
        assert con.execute("SELECT COUNT(*) FROM mart_vintage").fetchone()[0]>20
        assert con.execute("SELECT COUNT(*) FROM mart_roll_rates").fetchone()[0]>0
        assert con.execute("SELECT COUNT(*) FROM mart_customer_360").fetchone()[0]>0
        rates=con.execute("SELECT MAX(roll_rate_pct) FROM mart_roll_rates").fetchone()[0]
        assert rates <=100.0


def test_supervised_label_equals_next_month_servicing(pipeline_output):
    root,_,_,_=pipeline_output
    with sqlite3.connect(root/"warehouse"/"bankpulse.sqlite") as con:
        df=pd.read_sql_query("SELECT account_id,snapshot_month,days_past_due,next_month_dpd,target_next_30dpd FROM v_features ORDER BY account_id,snapshot_month",con)
    latest=df.groupby("account_id").tail(1)
    assert latest.target_next_30dpd.isna().all()
    positive=df[df.target_next_30dpd.eq(1)]
    assert len(positive)>5
    assert positive.days_past_due.lt(30).all()
    assert positive.next_month_dpd.ge(30).all()
    negative=df[df.target_next_30dpd.eq(0)]
    assert negative.next_month_dpd.lt(30).all()


def test_model_uses_time_holdout_and_no_future_feature(pipeline_output):
    root,_,model,_=pipeline_output
    assert "next_month_dpd" not in FEATURES
    assert "target_next_30dpd" not in FEATURES
    split=model["split"]
    assert split["train_months"][1] < split["validation_months"][0]
    assert split["validation_months"][1] < split["test_months"][0]
    assert model["test_metrics"]["roc_auc"]>=0 and model["test_metrics"]["roc_auc"]<=1
    assert model["test_metrics"]["events"]>0
    with sqlite3.connect(root/"warehouse"/"bankpulse.sqlite") as con:
        row=con.execute("SELECT COUNT(*),MIN(risk_score),MAX(risk_score) FROM mart_model_scores").fetchone()
        assert row[0]==split["test_rows"]
        assert 0<=row[1]<=row[2]<=1
        assert con.execute("SELECT COUNT(*) FROM mart_model_scores WHERE days_past_due >=30").fetchone()[0]==0


def test_dashboard_contains_real_kpis_and_chart_assets(pipeline_output):
    root,_,model,dashboard=pipeline_output
    html=dashboard.read_text()
    assert dashboard.stat().st_size>100000
    assert "BankPulse / Risk Intelligence" in html
    assert "30+ DPD account rate" in html
    assert "Outstanding exposure" in html
    assert "plotly" in html.lower()
    assert (root/"reports"/"MODEL_CARD.md").is_file()
    assert (root/"models"/"early_warning_model.joblib").stat().st_size>1000
    stored=json.loads((root/"reports"/"model_metrics.json").read_text())
    assert stored["selected_model"]==model["selected_model"]
