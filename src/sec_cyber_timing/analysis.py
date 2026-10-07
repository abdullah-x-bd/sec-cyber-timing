from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf


def deadline_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    counts = (
        frame.dropna(subset=["delay_business_days"])
        .groupby("delay_business_days", as_index=False)
        .size()
        .rename(columns={"size": "n"})
        .sort_values("delay_business_days")
    )
    counts["share"] = counts["n"] / counts["n"].sum()
    return counts


def fit_timing_lpm(frame: pd.DataFrame, outcome: str):
    data = frame.dropna(subset=[outcome, "is_item_105", "cik", "year_month"]).copy()
    data[outcome] = data[outcome].astype(int)
    data["is_item_105"] = data["is_item_105"].astype(int)

    model = smf.ols(
        f"{outcome} ~ is_item_105 + C(cik) + C(year_month)",
        data=data,
    )
    return model.fit(cov_type="cluster", cov_kwds={"groups": data["cik"]})
