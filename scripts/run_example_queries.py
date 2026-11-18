"""Execute named senior-level SQL interview examples on a generated warehouse."""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
db_path=ROOT/"warehouse"/"bankpulse.sqlite"
if not db_path.exists():
    raise SystemExit('Run `python run.py all` first.')
queries=[q.strip() for q in (ROOT/"sql"/"02_interview_queries.sql").read_text().split(';') if 'SELECT' in q.upper()]
with sqlite3.connect(db_path) as con:
    for i,sql in enumerate(queries,1):
        print(f"\n---- Analyst SQL query {i} ----")
        try: print(pd.read_sql_query(sql,con).to_string(index=False,max_rows=20))
        except Exception as e: raise RuntimeError(f"Failed sample SQL #{i}: {e}") from e
