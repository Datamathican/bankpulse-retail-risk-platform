"""OOT model selection, transparent evaluation, and scored portfolio outputs."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss, precision_score, recall_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from .pipeline import connect

NUMERIC = ["monthly_income_gbp","credit_limit_gbp","apr","outstanding_balance_gbp","utilisation","payment_ratio","inflow_3m_gbp","outflow_3m_gbp","returned_payments_3m","late_count_3m","previous_dpd","account_age_months"]
CATEGORICAL = ["product_type","region","employment_type"]
FEATURES = NUMERIC + CATEGORICAL


def chronological_splits(df:pd.DataFrame):
    """Choose training, validation and held-out test by month, never random row split."""
    months = sorted(df.snapshot_month.unique())
    if len(months)<8:
        raise ValueError("Need at least 8 labeled months to run chronological validation and test.")
    test_start = months[-3]
    validation_start = months[-5]
    train = df[df.snapshot_month < validation_start].copy()
    val = df[(df.snapshot_month >= validation_start) & (df.snapshot_month < test_start)].copy()
    test = df[df.snapshot_month >= test_start].copy()
    return train,val,test


def _make_pipeline(algorithm:str, seed:int):
    pre = ColumnTransformer([
        ("numeric",Pipeline([("imputer",SimpleImputer(strategy="median")),("scale",StandardScaler())]),NUMERIC),
        ("categorical",Pipeline([("imputer",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),CATEGORICAL)
    ])
    clf = LogisticRegression(max_iter=700,random_state=seed) if algorithm=="logistic_regression" else RandomForestClassifier(n_estimators=65,min_samples_leaf=15,n_jobs=-1,random_state=seed)
    return Pipeline([("preprocess",pre),("model",clf)])


def _metrics(y, scores, threshold:float):
    result = {"rows":len(y),"events":int(np.sum(y)),"event_rate":float(np.mean(y)),
              "roc_auc":float(roc_auc_score(y,scores)) if len(set(y))>1 else None,
              "average_precision":float(average_precision_score(y,scores)) if len(set(y))>1 else None,
              "brier":float(brier_score_loss(y,scores)),
              "alert_precision":float(precision_score(y,scores>=threshold,zero_division=0)),
              "alert_recall":float(recall_score(y,scores>=threshold,zero_division=0)),
              "alert_rate":float(np.mean(scores>=threshold))}
    top_n = max(1,int(np.ceil(.1*len(y))))
    idx=np.argsort(scores)[-top_n:]
    result["top_decile_event_capture"] = float(np.sum(np.asarray(y)[idx])/max(np.sum(y),1))
    return result


def _psi(expected,actual,bins=10):
    """Population stability index on utilisation; illustrative monitoring only."""
    e=np.asarray(expected,dtype=float)
    a=np.asarray(actual,dtype=float)
    e=e[np.isfinite(e)];a=a[np.isfinite(a)]
    if not len(e) or not len(a):return None
    edges=np.unique(np.quantile(e,np.linspace(0,1,bins+1)))
    if len(edges)<3:return 0.0
    edges[0]=-np.inf;edges[-1]=np.inf
    ec=np.histogram(e,bins=edges)[0]/len(e)
    ac=np.histogram(a,bins=edges)[0]/len(a)
    ec=np.clip(ec,1e-4,None); ac=np.clip(ac,1e-4,None)
    return float(np.sum((ac-ec)*np.log(ac/ec)))


def train_and_score(output_dir:Path,seed:int=42)->dict:
    root=Path(output_dir)
    with connect(root) as con:
        frame=pd.read_sql_query("SELECT * FROM v_features WHERE target_next_30dpd IS NOT NULL AND days_past_due < 30",con)
    if frame.empty: raise ValueError("No eligible labeled observations")
    frame["target_next_30dpd"]=frame.target_next_30dpd.astype(int)
    for col in NUMERIC:
        frame[col]=pd.to_numeric(frame[col],errors="coerce")
    train,val,test=chronological_splits(frame)
    ytr=train.target_next_30dpd.to_numpy()
    yval=val.target_next_30dpd.to_numpy()
    ytest=test.target_next_30dpd.to_numpy()
    if any(len(set(y))<2 for y in (ytr,yval,ytest)):
        raise ValueError("Insufficient synthetic positive and negative cases for holdout evaluation: try --customers 600")
    candidates={}
    for algo in ["logistic_regression","random_forest"]:
        clf=_make_pipeline(algo,seed)
        clf.fit(train[FEATURES],ytr)
        pred=clf.predict_proba(val[FEATURES])[:,1]
        candidates[algo]={"roc_auc":float(roc_auc_score(yval,pred)),"average_precision":float(average_precision_score(yval,pred))}
    chosen=max(candidates,key=lambda model:(candidates[model]["roc_auc"],candidates[model]["average_precision"]))
    # Threshold set entirely from validation distribution before the final test.
    val_model=_make_pipeline(chosen,seed).fit(train[FEATURES],ytr)
    val_scores=val_model.predict_proba(val[FEATURES])[:,1]
    threshold=float(np.quantile(val_scores,.9))
    dev=pd.concat([train,val],ignore_index=True)
    fitted=_make_pipeline(chosen,seed).fit(dev[FEATURES],dev.target_next_30dpd.astype(int))
    preds=fitted.predict_proba(test[FEATURES])[:,1]
    result={
        "problem":"Predict first transition to >=30 days past due in the following calendar month; only score accounts currently <30 DPD.",
        "data_classification":"100% synthetic; no actual personal or bank data",
        "selected_model":chosen,
        "candidate_validation_metrics":candidates,
        "risk_alert_threshold":threshold,
        "split":{"train_months":[str(train.snapshot_month.min()),str(train.snapshot_month.max())],
                 "validation_months":[str(val.snapshot_month.min()),str(val.snapshot_month.max())],
                 "test_months":[str(test.snapshot_month.min()),str(test.snapshot_month.max())],
                 "train_rows":len(train),"validation_rows":len(val),"test_rows":len(test)},
        "test_metrics":_metrics(ytest,preds,threshold),
        "utilisation_psi_dev_vs_test":_psi(dev.utilisation,test.utilisation),
        "features":FEATURES,
        "cautions":["Synthetic performance is not proof of real-world generalisation", "Not regulatory PD, IFRS 9 impairment, or production lending decisioning", "No protected characteristics used as direct model features", "No causal interpretation of ML predictors", "Monthly servicing is known before the following month's outcome"]
    }
    models=root/"models";reports=root/"reports"
    models.mkdir(parents=True,exist_ok=True);reports.mkdir(parents=True,exist_ok=True)
    joblib.dump(fitted,models/"early_warning_model.joblib")
    (reports/"model_metrics.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    scored=test[["account_id","snapshot_month","product_type","region","outstanding_balance_gbp","days_past_due","target_next_30dpd"]].copy()
    scored["risk_score"]=np.round(preds,6)
    scored["risk_alert"]=(preds>=threshold).astype(int)
    scored["risk_band"]=np.where(preds>=threshold,"High",np.where(preds>=np.median(preds),"Medium","Low"))
    with connect(root) as con:
        scored.to_sql("mart_model_scores",con,if_exists="replace",index=False)
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_scores ON mart_model_scores(account_id,snapshot_month)")
    card=f"""# Model card — BankPulse month-ahead delinquency early warning

**This is a research demonstration trained entirely on artificially generated data. Not for customer decisions.**

## Intended prediction
{result['problem']}

## Dataset and validation
- Train: {result['split']['train_months'][0]} to {result['split']['train_months'][1]} ({len(train):,} rows)
- Validation: {result['split']['validation_months'][0]} to {result['split']['validation_months'][1]} ({len(val):,} rows)
- Strict held-out test: {result['split']['test_months'][0]} to {result['split']['test_months'][1]} ({len(test):,} rows)
- No random row splitting: accounts can appear in multiple months, so time-wise holdout is essential.
- Label is next month's observed >=30 DPD; last month has no target and is never used for training.

## Model selection (validation only)
- Logistic regression validation ROC AUC: {candidates['logistic_regression']['roc_auc']:.3f}
- Random forest validation ROC AUC: {candidates['random_forest']['roc_auc']:.3f}
- Selected: **{chosen}**; refitted on train + validation, tested once.
- Alert cutoff: validation upper decile of scores = **{threshold:.3f}** (operational triage demonstration).

## Held-out performance
- ROC AUC: **{result['test_metrics']['roc_auc']:.3f}**
- Average precision: **{result['test_metrics']['average_precision']:.3f}**
- Brier score: **{result['test_metrics']['brier']:.3f}**
- Top-decile event capture: **{result['test_metrics']['top_decile_event_capture']:.1%}**
- High-risk alert precision: **{result['test_metrics']['alert_precision']:.1%}**
- High-risk alert recall: **{result['test_metrics']['alert_recall']:.1%}**
- Utilisation PSI (development vs test): **{result['utilisation_psi_dev_vs_test']:.3f}** (illustrative; should be tracked over time).

## Governance and limitations
- Entirely synthetic, so AUC values reflect the simulator's assumptions, not bank evidence.
- No individual automated decisions; not approved for lending, arrears treatment, regulatory capital or impairment.
- Sensitive or protected attributes are not direct features; a real deployment needs formal fairness testing, explainability and customer outcomes review.
- Current-period servicing and trailing three-month cashflow are features; future DPD is label only.
- Observe performance, calibration and selection bias on representative production data before any use.
- Analysts must validate the account grain, 30-day definition, observation timestamp and treatment of missing months.
"""
    (reports/"MODEL_CARD.md").write_text(card,encoding="utf8")
    return result
