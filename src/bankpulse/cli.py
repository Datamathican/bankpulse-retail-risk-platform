"""Simple, no-cloud commands for the complete project."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .simulate import generate_raw
from .pipeline import build_warehouse
from .model import train_and_score
from .report import build_report


def main(argv=None):
    parser=argparse.ArgumentParser(description="BankPulse: synthetic data -> SQL analytics -> risk ML -> offline dashboard")
    parser.add_argument("command",choices=["all","generate","build","train","report"],nargs="?",default="all")
    parser.add_argument("--customers",type=int,default=1200,help="Fictional customers for data generation (default: 1200)")
    parser.add_argument("--months",type=int,default=30,help="Monthly snapshots starting Jan 2024 (default: 30)")
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--quality-threshold",type=float,default=.03,help="Maximum source rejection rate, default 3%%")
    parser.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parents[2],help="Project/output folder")
    args=parser.parse_args(argv)
    root=args.output_dir.resolve()
    sql=Path(__file__).resolve().parents[2]/"sql"/"01_analytics_marts.sql"
    if args.command in ("all","generate"):
        print("[1/4] Generating fully synthetic banking data...",flush=True)
        print(json.dumps(generate_raw(root,args.customers,args.months,args.seed),indent=2),flush=True)
    if args.command in ("all","build"):
        print("[2/4] Applying data quality gates; materialising SQL warehouse...",flush=True)
        res=build_warehouse(root,sql,args.quality_threshold)
        print(json.dumps({k:v for k,v in res.items() if k!='checks'},indent=2),flush=True)
    if args.command in ("all","train"):
        print("[3/4] Validating, selecting and testing risk models...",flush=True)
        res=train_and_score(root,args.seed)
        print(json.dumps({"selected_model":res["selected_model"],"holdout":res["test_metrics"],"split":res["split"]},indent=2),flush=True)
    if args.command in ("all","report"):
        print("[4/4] Creating interactive offline executive dashboard...",flush=True)
        print(f"DASHBOARD: {build_report(root)}",flush=True)
    print("COMPLETE",flush=True)


if __name__=="__main__": main()
