"""Optional live UI. Run after pipeline: streamlit run app/streamlit_app.py"""
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"warehouse"/"bankpulse.sqlite"
st.set_page_config(page_title="BankPulse | Risk Intelligence",page_icon="🏦",layout="wide")
st.title("🏦 BankPulse — Banking Risk Intelligence")
st.caption("Portfolio control tower · Entirely synthetic data · Not for real lending decisions")
if not DB.exists():
    st.error("Please run `python run.py all` in the project folder first.")
    st.stop()

@st.cache_data(ttl=120)
def get_tables():
    with sqlite3.connect(DB) as con:
        monthly=pd.read_sql_query("SELECT * FROM mart_portfolio_monthly ORDER BY snapshot_month",con)
        segment=pd.read_sql_query("SELECT * FROM mart_risk_segment",con)
        quality=pd.read_sql_query("SELECT * FROM dq_checks",con)
        try: scores=pd.read_sql_query("SELECT * FROM mart_model_scores",con)
        except sqlite3.OperationalError: scores=pd.DataFrame()
    return monthly,segment,quality,scores
monthly,segment,quality,scores=get_tables()
months=sorted(monthly.snapshot_month.unique())
selected=st.sidebar.selectbox("Portfolio month",months,index=len(months)-1)
products=sorted(segment.product_type.unique())
chosen=st.sidebar.multiselect("Product",products,default=products)
regions=sorted(segment.region.unique())
chosen_regions=st.sidebar.multiselect("Region",regions,default=regions)
filtered=segment[(segment.snapshot_month==selected)&segment.product_type.isin(chosen)&segment.region.isin(chosen_regions)]
if filtered.empty:
    st.warning("No records match your filters")
    st.stop()
assets=float(filtered.exposure_gbp.sum());n=int(filtered.accounts.sum());bad=int(filtered.accounts_30plus.sum())
k1,k2,k3,k4=st.columns(4)
k1.metric("Outstanding balance",f"£{assets/1e6:.2f}m")
k2.metric("Accounts",f"{n:,}")
k3.metric("30+ DPD rate",f"{100*bad/n:.2f}%")
k4.metric("Latest data month",selected)
t1,t2,t3=st.tabs(["Portfolio analytics","Risk model and scores","Data quality"])
with t1:
    p1,p2=st.columns(2)
    p1.plotly_chart(px.line(monthly,x="snapshot_month",y="total_exposure_gbp",markers=True,title="Portfolio balance trend"),use_container_width=True)
    p2.plotly_chart(px.line(monthly,x="snapshot_month",y="pct_accounts_30plus",markers=True,title="30+ DPD account rate"),use_container_width=True)
    st.plotly_chart(px.bar(filtered,x="region",y="accounts_30plus",color="product_type",title="Delinquent accounts by product and region"),use_container_width=True)
    st.dataframe(filtered.sort_values("exposure_gbp",ascending=False),use_container_width=True,hide_index=True)
with t2:
    if scores.empty:st.warning("Run `python run.py train` to create model predictions")
    else:
        st.info("These scores apply only to the held-out evaluation months; they are not live production predictions.")
        st.plotly_chart(px.histogram(scores,x="risk_score",color="risk_band",nbins=30,title="Holdout risk score distribution"),use_container_width=True)
        st.dataframe(scores.sort_values("risk_score",ascending=False).head(250),use_container_width=True,hide_index=True)
with t3:
    st.dataframe(quality,use_container_width=True,hide_index=True)
    st.bar_chart(quality.groupby("source_table").failed_count.sum())
