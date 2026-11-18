"""Transparent row-level quarantine and source data quality reporting."""
from __future__ import annotations
import pandas as pd


class QualityGate:
    def __init__(self):
        self.checks: list[dict] = []
        self.quarantine: list[dict] = []

    def apply(self, source: str, frame: pd.DataFrame, checks: list[tuple[str, pd.Series]], key: str) -> pd.DataFrame:
        """For every check, True represents a failed row. Quarantine the union."""
        bad = pd.Series(False,index=frame.index)
        for rule, mask in checks:
            mask = mask.fillna(True).astype(bool)
            self.checks.append({"source_table":source,"rule_id":rule,"records_checked":len(frame),"failed_count":int(mask.sum()),"severity":"error"})
            for idx in frame.index[mask]:
                self.quarantine.append({"source_table":source,"record_key":str(frame.at[idx,key]),"rule_id":rule,"reason":"Failed quality gate"})
            bad = bad | mask
        return frame.loc[~bad].copy()

    def assert_clean(self, bad_rate_limit: float = .03):
        # Rates are based on distinct quarantined record keys by source (not rule count).
        per_source = {}
        for item in self.quarantine:
            per_source.setdefault(item['source_table'],set()).add(item['record_key'])
        for source, keys in per_source.items():
            n = max((x['records_checked'] for x in self.checks if x['source_table']==source),default=1)
            if len(keys)/max(n,1)>bad_rate_limit:
                raise ValueError(f"Data quality gate failed for {source}: {len(keys)}/{n} rows invalid (> {bad_rate_limit:.0%}). Inspect quarantine events.")


def duplicate_mask(frame: pd.DataFrame, cols: str | list[str]) -> pd.Series:
    return frame.duplicated(subset=cols,keep='first')
