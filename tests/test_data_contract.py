import hashlib
from pathlib import Path
import sqlite3
import pandas as pd
import pytest
from bankpulse.simulate import generate_raw
from bankpulse.pipeline import build_warehouse


def test_synthetic_data_deterministic(tmp_path):
    for sub in ("one","two"):
        generate_raw(tmp_path/sub,customers=35,months=10,seed=99)
    for name in ("customers","accounts","transactions","servicing"):
        a=(tmp_path/"one"/"data"/"raw"/f"{name}.csv").read_bytes()
        b=(tmp_path/"two"/"data"/"raw"/f"{name}.csv").read_bytes()
        assert hashlib.sha256(a).digest()==hashlib.sha256(b).digest()


def test_generator_rejects_too_short_dataset(tmp_path):
    with pytest.raises(ValueError): generate_raw(tmp_path,customers=5,months=4)


def test_quality_quarantine_and_referential_integrity(pipeline_output):
    root,dq,_,_=pipeline_output
    assert dq["quarantined_distinct_rows"]>=8
    assert dq["failed_quality_rules"]>=4
    with sqlite3.connect(root/"warehouse"/"bankpulse.sqlite") as conn:
        assert conn.execute("SELECT COUNT(*) FROM quarantine_events").fetchone()[0]>=8
        assert conn.execute("SELECT COUNT(*) FROM fact_transaction t LEFT JOIN dim_account a USING(account_id) WHERE a.account_id IS NULL").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM fact_servicing s LEFT JOIN dim_account a USING(account_id) WHERE a.account_id IS NULL").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*)-COUNT(DISTINCT transaction_id) FROM fact_transaction").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM dim_customer WHERE monthly_income_gbp <= 0").fetchone()[0]==0


def test_quality_gate_fail_closed(tmp_path):
    generate_raw(tmp_path,customers=40,months=10,seed=2)
    sql=Path(__file__).resolve().parents[1]/"sql"/"01_analytics_marts.sql"
    with pytest.raises(ValueError,match="Data quality gate failed"):
        build_warehouse(tmp_path,sql,threshold=0.0)
    assert not (tmp_path/"warehouse"/"bankpulse.sqlite").exists()
