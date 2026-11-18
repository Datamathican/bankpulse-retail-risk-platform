"""Generate a browser-openable, offline Plotly executive dashboard."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
from .pipeline import connect


def build_report(output_dir:Path)->Path:
    root=Path(output_dir)
    with connect(root) as db:
        monthly=pd.read_sql_query("SELECT * FROM mart_portfolio_monthly ORDER BY snapshot_month",db)
        segments=pd.read_sql_query("SELECT * FROM mart_risk_segment",db)
        dqs=pd.read_sql_query("SELECT source_table, SUM(failed_count) AS failed_checks FROM dq_checks GROUP BY source_table",db)
        roll=pd.read_sql_query("SELECT from_bucket,to_bucket,SUM(accounts) AS accounts FROM mart_roll_rates GROUP BY from_bucket,to_bucket",db)
        try:
            scores=pd.read_sql_query("SELECT * FROM mart_model_scores",db)
        except (pd.errors.DatabaseError, sqlite3.OperationalError):
            scores=pd.DataFrame()
    metrics_path=root/"reports"/"model_metrics.json"
    metrics=json.loads(metrics_path.read_text()) if metrics_path.exists() else None
    last=monthly.iloc[-1]
    newest=str(last.snapshot_month)
    current=segments[segments.snapshot_month==newest]
    theme=dict(template="plotly_white",font=dict(family="Arial",size=13,color="#16314a"),margin=dict(l=40,r=16,t=48,b=44),paper_bgcolor="#ffffff",plot_bgcolor="#ffffff")
    balance=px.line(monthly,x="snapshot_month",y="total_exposure_gbp",markers=True,title="Outstanding exposure through time",labels={"total_exposure_gbp":"GBP","snapshot_month":"Month"})
    balance.update_layout(**theme)
    arrears=px.line(monthly,x="snapshot_month",y="pct_accounts_30plus",markers=True,title="30+ DPD account rate",labels={"pct_accounts_30plus":"Accounts %","snapshot_month":"Month"})
    arrears.update_layout(**theme)
    regions=current.groupby("region",as_index=False).agg(accounts=("accounts","sum"),exposure_gbp=("exposure_gbp","sum"),delinquent=("accounts_30plus","sum"))
    regions["pct_30plus"]=100*regions.delinquent/regions.accounts
    region_fig=px.bar(regions.sort_values("pct_30plus",ascending=False),x="region",y="pct_30plus",color="region",title="Delinquency by region — latest month",labels={"pct_30plus":"30+ DPD %"})
    region_fig.update_layout(**theme,showlegend=False)
    products=current.groupby("product_type",as_index=False).agg(exposure_gbp=("exposure_gbp","sum"))
    product_fig=px.pie(products,names="product_type",values="exposure_gbp",hole=.55,title="Exposure mix by product")
    product_fig.update_layout(**theme)
    dqfig=px.bar(dqs,x="source_table",y="failed_checks",title="Rejected rule events by source",labels={"failed_checks":"Rule failures","source_table":"Source"})
    dqfig.update_layout(**theme)
    roll=roll.sort_values("accounts",ascending=False).head(12)
    rollfig=px.bar(roll,x="from_bucket",y="accounts",color="to_bucket",title="Delinquency bucket migrations",labels={"accounts":"Transitions","from_bucket":"From status","to_bucket":"To status"})
    rollfig.update_layout(**theme)
    figures=[balance,arrears,region_fig,product_fig,dqfig,rollfig]
    if not scores.empty:
        scores["observed"]=scores.target_next_30dpd.map({0:"No new 30+ DPD",1:"New 30+ DPD"})
        hist=px.histogram(scores,x="risk_score",color="observed",nbins=32,barmode="overlay",opacity=.7,title="Held-out risk scores vs observed next-month outcome")
        hist.update_layout(**theme)
        figures.append(hist)
    js_first=True
    plots=[]
    for fig in figures:
        plots.append(plot(fig,output_type="div",include_plotlyjs="inline" if js_first else False,config={"displaylogo":False,"responsive":True}))
        js_first=False
    cards=[("Outstanding exposure",f"£{float(last.total_exposure_gbp)/1e6:,.2f}m"),
           ("Active accounts",f"{int(last.accounts):,}"),
           ("30+ DPD accounts",f"{float(last.pct_accounts_30plus):,.2f}%"),
           ("Rejected quality events",f"{int(dqs.failed_checks.sum()):,}")]
    if metrics:
        cards.append(("Held-out ROC AUC",f"{metrics['test_metrics']['roc_auc']:.3f}"))
        cards.append(("Top 10% event capture",f"{metrics['test_metrics']['top_decile_event_capture']:.1%}"))
    card_html="".join(f'<div class="kpi"><div class="label">{title}</div><div class="number">{value}</div></div>' for title,value in cards)
    chart_html="".join(f'<section class="panel">{plot_html}</section>' for plot_html in plots)
    html=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>BankPulse | Executive Risk Intelligence</title>
    <style>body{{margin:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#15324c}}
    header{{background:linear-gradient(110deg,#102b45,#1c627b);color:#fff;padding:33px max(24px,calc((100vw - 1230px)/2));}}
    header h1{{font-size:32px;margin:0 0 10px}}header p{{margin:0;color:#dceefa;font-size:15px}}
    main{{max-width:1230px;margin:auto;padding:22px}}.meta{{font-size:13px;color:#52657a;margin-bottom:19px}}
    .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:13px;margin-bottom:18px}}
    .kpi{{background:#fff;border-radius:12px;padding:21px;box-shadow:0 1px 4px #c8d3dc}}
    .label{{color:#66798b;font-size:12px;text-transform:uppercase;letter-spacing:.6px}}.number{{font-size:26px;font-weight:bold;margin-top:8px;color:#153956}}
    .charts{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}}.panel{{background:#fff;border-radius:12px;overflow:hidden;min-height:350px;box-shadow:0 1px 4px #c8d3dc}}
    .panel .plotly-graph-div{{width:100%!important}}footer{{font-size:13px;color:#66798b;margin:25px 0 45px;line-height:1.6}}
    @media(max-width:800px){{.charts{{grid-template-columns:1fr}}}}
    </style></head><body><header><h1>BankPulse / Risk Intelligence</h1><p>Retail banking portfolio monitoring, early-warning analytics and trusted data</p></header>
    <main><p class="meta">Latest portfolio snapshot: <b>{newest}</b> · 100% synthetic data · Historical labels are not live forecasts · Offline dashboard</p>
    <div class="kpis">{card_html}</div><div class="charts">{chart_html}</div>
    <footer>DEMONSTRATION ONLY — This analysis uses simulated customers and transactions. The model does not meet bank governance or regulatory approval requirements. Methodology and reproducibility: see README.md, docs/ and reports/MODEL_CARD.md.</footer></main></body></html>"""
    dest=root/"dashboard"/"index.html"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(html,encoding="utf8")
    return dest
