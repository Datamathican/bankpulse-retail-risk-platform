"""CSV bronze -> validated SQLite silver -> SQL gold marts."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
import pandas as pd
from .quality import QualityGate, duplicate_mask
from .simulate import PRODUCTS


def connect(output_dir: Path) -> sqlite3.Connection:
    db = Path(output_dir)/"warehouse"/"bankpulse.sqlite"
    if not db.exists():
        raise FileNotFoundError(f"Warehouse missing: {db}. Run 'python run.py build' first.")
    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _read_raw(root:Path,name:str) -> pd.DataFrame:
    path = root/"data"/"raw"/f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing source {path}; first run 'python run.py generate'")
    return pd.read_csv(path,dtype=str,keep_default_na=False)


def _parse_num(frame:pd.DataFrame,columns:list[str]):
    for c in columns:
        frame[c] = pd.to_numeric(frame[c],errors="coerce")


def build_warehouse(output_dir: Path, sql_path: Path, threshold:float=.03)->dict:
    root = Path(output_dir)
    q = QualityGate()
    c = _read_raw(root,"customers")
    _parse_num(c,["monthly_income_gbp"])
    c = q.apply("customers",c,[
        ("customer_id_required", c.customer_id.eq("")),
        ("customer_unique", duplicate_mask(c,"customer_id")),
        ("valid_income",c.monthly_income_gbp.isna() | c.monthly_income_gbp.le(0)),
        ("valid_region",c.region.eq(""))],"customer_id")
    a = _read_raw(root,"accounts")
    _parse_num(a,["credit_limit_gbp","apr"])
    a = q.apply("accounts",a,[
        ("account_id_required", a.account_id.eq("")),
        ("account_unique", duplicate_mask(a,"account_id")),
        ("account_customer_fk", ~a.customer_id.isin(c.customer_id)),
        ("account_product_enum",~a.product_type.isin(PRODUCTS)),
        ("positive_credit_limit",a.credit_limit_gbp.isna() | a.credit_limit_gbp.le(0)),
        ("valid_apr",a.apr.isna() | ~a.apr.between(0,1)),
        ("valid_origination", ~a.origination_month.str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])"))],"account_id")
    t = _read_raw(root,"transactions")
    _parse_num(t,["amount_gbp"])
    t = q.apply("transactions",t,[
        ("txn_unique",duplicate_mask(t,"transaction_id")),
        ("txn_account_fk",~t.account_id.isin(a.account_id)),
        ("txn_amount_valid",t.amount_gbp.isna() | t.amount_gbp.eq(0) | t.amount_gbp.abs().gt(50000)),
        ("txn_date_valid",pd.to_datetime(t.transaction_date,errors="coerce").isna())],"transaction_id")
    s = _read_raw(root,"servicing")
    _parse_num(s,["outstanding_balance_gbp","days_past_due","minimum_payment_gbp","payment_received_gbp"])
    limit_lookup = a.set_index("account_id")["credit_limit_gbp"]
    account_limit = s.account_id.map(limit_lookup)
    s = q.apply("servicing",s,[
        ("account_month_unique",duplicate_mask(s,["account_id","snapshot_month"])),
        ("servicing_account_fk",~s.account_id.isin(a.account_id)),
        ("valid_dpd",s.days_past_due.isna() | ~s.days_past_due.between(0,180) | s.days_past_due.mod(1).ne(0)),
        ("valid_outstanding_balance",s.outstanding_balance_gbp.isna() | s.outstanding_balance_gbp.lt(0) | s.outstanding_balance_gbp.gt(account_limit*1.25)),
        ("valid_minimum_payment",s.minimum_payment_gbp.isna() | s.minimum_payment_gbp.lt(0)),
        ("valid_received_payment",s.payment_received_gbp.isna() | s.payment_received_gbp.lt(0)),
        ("valid_snapshot_month",~s.snapshot_month.str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])"))],"account_id")
    # Fail closed, before any output is published.
    q.assert_clean(threshold)
    path = root/"warehouse"/"bankpulse.sqlite"
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as db:
        for name,df in [("dim_customer",c),("dim_account",a),("fact_transaction",t),("fact_servicing",s)]:
            df.to_sql(name,db,index=False,if_exists="replace")
        pd.DataFrame(q.checks).to_sql("dq_checks",db,index=False,if_exists="replace")
        pd.DataFrame(q.quarantine,columns=["source_table","record_key","rule_id","reason"]).to_sql("quarantine_events",db,index=False,if_exists="replace")
        db.executescript("""
            CREATE UNIQUE INDEX idx_c ON dim_customer(customer_id);
            CREATE UNIQUE INDEX idx_a ON dim_account(account_id);
            CREATE UNIQUE INDEX idx_t ON fact_transaction(transaction_id);
            CREATE UNIQUE INDEX idx_s ON fact_servicing(account_id,snapshot_month);
            CREATE INDEX idx_txn ON fact_transaction(account_id, transaction_date);
            CREATE INDEX idx_serv_month ON fact_servicing(snapshot_month);
        """)
        db.executescript(Path(sql_path).read_text(encoding='utf8'))
        db.execute("PRAGMA integrity_check")
    reports = root/"reports"
    reports.mkdir(parents=True,exist_ok=True)
    info = {
        "warehouse":str(path),
        "clean_rows":{"customers":len(c),"accounts":len(a),"transactions":len(t),"servicing":len(s)},
        "quarantined_events":len(q.quarantine),
        "quarantined_distinct_rows":sum(len(set(x['record_key'] for x in q.quarantine if x['source_table']==tbl)) for tbl in ['customers','accounts','transactions','servicing']),
        "failed_quality_rules":sum(x['failed_count']>0 for x in q.checks),
        "checks":q.checks,
        "note":"Synthetic source errors are deliberately injected as a reproducible test of the quarantine mechanism."
    }
    (reports/"data_quality.json").write_text(json.dumps(info,indent=2),encoding="utf8")
    return info
