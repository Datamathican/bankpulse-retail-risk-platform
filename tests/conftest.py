from pathlib import Path
import pytest
from bankpulse.simulate import generate_raw
from bankpulse.pipeline import build_warehouse
from bankpulse.model import train_and_score
from bankpulse.report import build_report

@pytest.fixture(scope="module")
def pipeline_output(tmp_path_factory):
    root=tmp_path_factory.mktemp("full_bankpulse")
    generate_raw(root,customers=220,months=16,seed=17)
    sql=Path(__file__).resolve().parents[1]/"sql"/"01_analytics_marts.sql"
    quality=build_warehouse(root,sql)
    model=train_and_score(root,seed=17)
    dashboard=build_report(root)
    return root,quality,model,dashboard
