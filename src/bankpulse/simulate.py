"""Deterministic synthetic banking data. Never uses real customer information."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

REGIONS = ["London", "South East", "Midlands", "North West", "Scotland", "Wales"]
PRODUCTS = ["Credit Card", "Personal Loan", "Overdraft"]
TXN_CATEGORIES = ["Groceries", "Housing", "Bills", "Shopping", "Travel", "Dining", "Transport"]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))


def generate_raw(output_dir: Path, customers: int = 1200, months: int = 30, seed: int = 42, inject_issues: bool = True) -> dict:
    """Build reproducible, fictional customer/account/cashflow/servicing CSV files."""
    if customers < 30 or months < 10:
        raise ValueError("Provide at least 30 customers and 10 monthly snapshots")
    raw = Path(output_dir) / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=months, freq="MS")
    customer_rows, account_rows, txn_rows, service_rows = [], [], [], []
    for i in range(customers):
        cid = f"C{i+1:06d}"
        income = float(np.clip(rng.lognormal(np.log(2850), 0.45), 1100, 12000))
        region = str(rng.choice(REGIONS, p=[.23, .23, .19, .17, .10, .08]))
        employed = str(rng.choice(["Employed", "Self-employed", "Retired"], p=[.77,.16,.07]))
        age_band = str(rng.choice(["25-34", "35-44", "45-54", "55-64", "65+"]))
        customer_rows.append((cid, region, round(income, 2), employed, age_band))
        n_accounts = int(rng.choice([1, 2], p=[0.78,0.22]))
        customer_risk = float(rng.normal(0,.75)) + (income < 2100)*.35
        for a in range(n_accounts):
            aid = f"A{i+1:06d}{a+1}"
            product = str(rng.choice(PRODUCTS, p=[.52,.37,.11]))
            limit = float(round(rng.uniform(1500, 15000) if product != "Personal Loan" else rng.uniform(5000,40000), 2))
            apr = float(round(rng.uniform(.12,.30) if product=="Credit Card" else rng.uniform(.05,.18),4))
            origin_idx = int(rng.integers(0, min(months-8, 14)))
            origination = dates[origin_idx].strftime("%Y-%m")
            account_rows.append((aid,cid,product,limit,apr,origination))
            prev_dpd = 0
            util = float(rng.uniform(.18,.72))
            for j in range(origin_idx, months):
                mon = dates[j]
                month_s = mon.strftime("%Y-%m")
                macro_stress = .28 if mon.year >= 2025 and mon.month in (1,2,3) else 0.0
                stress = float(rng.normal(0,0.68)) + .42*customer_risk + macro_stress
                util = float(np.clip(util + rng.normal(.015 + .018*stress,.085),.035,.97))
                balance = round(limit*util,2)
                p_late = _sigmoid(-3.15 + .78*stress + 1.05*(util>.72) + .7*(prev_dpd>=5) + 1.35*(prev_dpd>=30))
                incident = rng.random() < p_late
                dpd = int(rng.choice([30,60,90],p=[.74,.20,.06])) if incident else (int(rng.choice([5,15],p=[.7,.3])) if rng.random()<.08 else 0)
                min_due = round(max(20,balance*(.025 if product != "Personal Loan" else .04)),2)
                paid = round(min_due*rng.uniform(.2,.75) if dpd>=30 else min_due*rng.uniform(.9,2.1),2)
                service_rows.append((aid,month_s,balance,dpd,min_due,paid))
                prev_dpd = dpd
                # Transaction stream: linked household cashflow proxy, not card-ledger settlement.
                if rng.random() < .95:
                    txn_rows.append((f"T{len(txn_rows)+1:09d}",aid,(mon+pd.Timedelta(days=int(rng.integers(0,25)))).strftime("%Y-%m-%d"),"Income",round(income*rng.uniform(.78,1.12),2)))
                n_spends = int(rng.integers(3,8))
                for _ in range(n_spends):
                    cat = str(rng.choice(TXN_CATEGORIES))
                    amount = float(np.clip(rng.lognormal(np.log(95),.75),5,1550))*(1+.14*max(stress,0))
                    txn_rows.append((f"T{len(txn_rows)+1:09d}",aid,(mon+pd.Timedelta(days=int(rng.integers(0,27)))).strftime("%Y-%m-%d"),cat,-round(amount,2)))
                if rng.random() < (.035 + .23*int(dpd>=30)):
                    txn_rows.append((f"T{len(txn_rows)+1:09d}",aid,(mon+pd.Timedelta(days=int(rng.integers(0,26)))).strftime("%Y-%m-%d"),"Returned Payment",-15.0))

    frames = {
        "customers": pd.DataFrame(customer_rows,columns=["customer_id","region","monthly_income_gbp","employment_type","age_band"]),
        "accounts": pd.DataFrame(account_rows,columns=["account_id","customer_id","product_type","credit_limit_gbp","apr","origination_month"]),
        "transactions": pd.DataFrame(txn_rows,columns=["transaction_id","account_id","transaction_date","category","amount_gbp"]),
        "servicing": pd.DataFrame(service_rows,columns=["account_id","snapshot_month","outstanding_balance_gbp","days_past_due","minimum_payment_gbp","payment_received_gbp"]),
    }
    if inject_issues:
        # Deliberately damaged bronze source rows for demonstrating quarantine and DQ metrics.
        frames["customers"] = pd.concat([frames["customers"],frames["customers"].iloc[[0]],pd.DataFrame([["C_BAD","London",-250,"Employed","25-34"]],columns=frames["customers"].columns)],ignore_index=True)
        frames["accounts"] = pd.concat([frames["accounts"],frames["accounts"].iloc[[0]],pd.DataFrame([["A_BAD","C_UNKNOWN","Credit Card",5000,.2,"2024-01"]],columns=frames["accounts"].columns)],ignore_index=True)
        frames["transactions"] = pd.concat([frames["transactions"],frames["transactions"].iloc[[0]],pd.DataFrame([["T_BAD","A_UNKNOWN","2025-03-01","Groceries",-20]],columns=frames["transactions"].columns)],ignore_index=True)
        frames["servicing"] = pd.concat([frames["servicing"],frames["servicing"].iloc[[0]],pd.DataFrame([["A_BAD","2025-02",1000,999,10,0]],columns=frames["servicing"].columns)],ignore_index=True)
    for name, frame in frames.items():
        frame.to_csv(raw/f"{name}.csv",index=False)
    return {"seed":seed,"customers":customers,"months":months,"raw_rows":{k:len(v) for k,v in frames.items()},"output":str(raw)}
