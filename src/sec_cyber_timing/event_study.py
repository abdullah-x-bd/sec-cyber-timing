from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def _window_slice(series: pd.Series | pd.DataFrame, event_pos: int, start: int, end: int):
    left = event_pos + start
    right = event_pos + end + 1
    if left < 0 or right > len(series):
        return series.iloc[0:0]
    return series.iloc[left:right]


def market_model_event(
    asset_prices: pd.Series,
    benchmark_prices: pd.Series,
    event_date: pd.Timestamp,
    estimation_start: int = -130,
    estimation_end: int = -30,
    event_windows: list[tuple[int, int]] | None = None,
) -> dict:
    event_windows = event_windows or [(-1, 1), (0, 1), (0, 2), (0, 5)]

    joined = pd.concat(
        {
            "asset": asset_prices.pct_change(),
            "benchmark": benchmark_prices.pct_change(),
        },
        axis=1,
    ).dropna()

    event_date = pd.Timestamp(event_date)
    if event_date not in joined.index:
        return {"event_date": event_date, "valid": False, "reason": "event_date_missing"}

    event_pos = joined.index.get_loc(event_date)
    estimation = _window_slice(joined, event_pos, estimation_start, estimation_end)
    if len(estimation) < 60:
        return {
            "event_date": event_date,
            "valid": False,
            "reason": "insufficient_estimation_window",
        }

    x = sm.add_constant(estimation["benchmark"])
    model = sm.OLS(estimation["asset"], x).fit()

    expected = model.params["const"] + model.params["benchmark"] * joined["benchmark"]
    abnormal = joined["asset"] - expected

    result = {
        "event_date": event_date,
        "valid": True,
        "alpha": float(model.params["const"]),
        "beta": float(model.params["benchmark"]),
        "estimation_n": int(len(estimation)),
    }

    for start, end in event_windows:
        window = _window_slice(abnormal, event_pos, start, end)
        key = f"car_{start}_{end}"
        result[key] = float(window.sum()) if len(window) == (end - start + 1) else np.nan

    return result
