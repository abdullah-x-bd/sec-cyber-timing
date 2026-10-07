from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

import pandas as pd

NY = ZoneInfo("America/New_York")


def normalize_acceptance_datetime(value: object) -> pd.Timestamp:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    if ts.tzinfo is None:
        return ts.tz_localize(NY)
    return ts.tz_convert(NY)


def add_timing_variables(frame: pd.DataFrame, market_close: str = "16:00") -> pd.DataFrame:
    out = frame.copy()
    out["acceptance_et"] = out["acceptanceDateTime"].map(normalize_acceptance_datetime)

    hour, minute = (int(part) for part in market_close.split(":"))
    close_time = time(hour, minute)

    out["after_hours"] = out["acceptance_et"].map(
        lambda ts: bool(ts.time() >= close_time) if not pd.isna(ts) else pd.NA
    )
    out["friday"] = out["filingDate"].map(
        lambda value: pd.Timestamp(value).weekday() == 4 if pd.notna(value) else pd.NA
    )
    out["year_month"] = (
        pd.to_datetime(out["filingDate"], errors="coerce")
        .dt.to_period("M")
        .astype(str)
    )
    return out
