from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import yfinance as yf
from scipy.stats import ttest_1samp, wilcoxon


ROOT = Path(__file__).resolve().parents[1]
HF_ROOT = Path("/tmp/sec-8k-events")
OUT = ROOT / "results" / "public_event_study"
OUT.mkdir(parents=True, exist_ok=True)


def load_parts(name: str) -> pd.DataFrame:
    files = sorted((HF_ROOT / "data" / name).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for {name}")
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)


def ticker_for_event(entity: pd.DataFrame, cik: str, event_date: pd.Timestamp) -> str | None:
    rows = entity.loc[
        entity["cik"].eq(cik) & entity["ticker"].notna()
    ].copy()
    if rows.empty:
        return None

    rows["valid_from"] = pd.to_datetime(rows["valid_from"], errors="coerce")
    rows["valid_to"] = pd.to_datetime(rows["valid_to"], errors="coerce")

    valid = rows.loc[
        (rows["valid_from"].isna() | rows["valid_from"].le(event_date))
        & (rows["valid_to"].isna() | rows["valid_to"].ge(event_date))
    ].copy()
    if valid.empty:
        valid = rows.copy()

    valid["current"] = valid["valid_from"].isna() & valid["valid_to"].isna()
    valid = valid.sort_values(["current", "valid_from"], ascending=[False, False])
    ticker = valid.iloc[0]["ticker"]
    return str(ticker) if pd.notna(ticker) else None


def event_day(row: pd.Series) -> pd.Timestamp:
    knowledge = pd.to_datetime(row["knowledge_date"], utc=True).tz_convert(
        "America/New_York"
    )
    session = str(row["market_session"])
    if session in {"pre_market", "regular_session"}:
        return pd.Timestamp(knowledge.date())

    next_open = pd.to_datetime(row["next_regular_session_open"], utc=True)
    if pd.isna(next_open):
        return pd.NaT
    return pd.Timestamp(next_open.tz_convert("America/New_York").date())


def get_close_panel(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    data = yf.download(
        sorted(set(tickers)),
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        close = data[["Close"]].copy()
        if len(tickers) == 1:
            close.columns = [tickers[0]]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.sort_index()


def market_model_event(
    prices: pd.DataFrame,
    ticker: str,
    event_date: pd.Timestamp,
    benchmark: str = "SPY",
) -> dict:
    if ticker not in prices.columns or benchmark not in prices.columns:
        return {"valid": False, "reason": "price_series_missing"}

    joined = pd.concat(
        {
            "asset": prices[ticker].pct_change(),
            "market": prices[benchmark].pct_change(),
        },
        axis=1,
    ).dropna()

    if event_date not in joined.index:
        return {"valid": False, "reason": "event_session_missing"}

    pos = joined.index.get_loc(event_date)
    if not isinstance(pos, (int, np.integer)):
        return {"valid": False, "reason": "duplicate_event_session"}

    est_start = pos - 130
    est_end = pos - 30
    if est_start < 0 or est_end <= est_start:
        return {"valid": False, "reason": "insufficient_history"}

    estimation = joined.iloc[est_start:est_end]
    if len(estimation) < 60:
        return {"valid": False, "reason": "insufficient_history"}

    fit = sm.OLS(
        estimation["asset"],
        sm.add_constant(estimation["market"]),
    ).fit()

    expected = fit.params["const"] + fit.params["market"] * joined["market"]
    abnormal = joined["asset"] - expected

    out = {
        "valid": True,
        "reason": "",
        "alpha": float(fit.params["const"]),
        "beta": float(fit.params["market"]),
        "estimation_n": len(estimation),
    }

    for start, end in [(-1, 1), (0, 1), (0, 2), (0, 5)]:
        left = pos + start
        right = pos + end + 1
        key = f"car_{start}_{end}"
        if left < 0 or right > len(abnormal):
            out[key] = np.nan
        else:
            out[key] = float(abnormal.iloc[left:right].sum())

    return out


def main() -> None:
    cyber = load_parts("cyber_events")
    filings = load_parts("filings")
    entity = load_parts("entity_map")

    cyber["cik"] = cyber["cik"].astype(str).str.zfill(10)
    filings["cik"] = filings["cik"].astype(str).str.zfill(10)
    entity["cik"] = entity["cik"].astype(str).str.zfill(10)

    cyber["knowledge_date"] = pd.to_datetime(
        cyber["knowledge_date"], errors="coerce", utc=True
    )
    cyber["knowledge_et"] = cyber["knowledge_date"].dt.tz_convert(
        "America/New_York"
    )
    start = pd.Timestamp("2024-06-15", tz="America/New_York")
    end = pd.Timestamp("2026-10-01", tz="America/New_York")

    sample = cyber.loc[
        ~cyber["is_amendment"].astype(bool)
        & cyber["knowledge_et"].between(start, end, inclusive="left")
    ].copy()
    sample = sample.drop_duplicates("accession_no")

    filing_cols = [
        "accession_no",
        "accepted_at_et",
        "items_raw",
        "knowledge_estimated",
    ]
    sample = sample.merge(
        filings[filing_cols].drop_duplicates("accession_no"),
        on="accession_no",
        how="left",
    )

    sample["event_session"] = sample.apply(event_day, axis=1)
    sample["ticker"] = sample.apply(
        lambda row: ticker_for_event(entity, row["cik"], row["event_session"]),
        axis=1,
    )

    accepted = pd.to_datetime(sample["accepted_at_et"], errors="coerce")
    minute = accepted.dt.hour * 60 + accepted.dt.minute + accepted.dt.second / 60
    sample["after_1600"] = minute.ge(16 * 60)
    sample["after_1630"] = minute.ge(16.5 * 60)
    sample["after_1700"] = minute.ge(17 * 60)

    ticker_list = sample["ticker"].dropna().unique().tolist()
    prices = get_close_panel(
        ticker_list + ["SPY"],
        start="2023-07-01",
        end="2026-10-08",
    )
    prices.to_csv(OUT / "adjusted_close_panel.csv", index_label="date")

    results = []
    for _, row in sample.iterrows():
        ticker = row["ticker"]
        event_session = row["event_session"]

        if not isinstance(ticker, str) or pd.isna(event_session):
            result = {"valid": False, "reason": "ticker_or_event_date_missing"}
        else:
            result = market_model_event(prices, ticker, event_session)

        result.update(
            {
                "accession_no": row["accession_no"],
                "cik": row["cik"],
                "company_name": row["company_name"],
                "ticker": ticker,
                "event_session": event_session,
                "market_session": row["market_session"],
                "after_1600": row["after_1600"],
                "after_1630": row["after_1630"],
                "after_1700": row["after_1700"],
                "knowledge_estimated": row["knowledge_estimated"],
            }
        )
        results.append(result)

    events = pd.DataFrame(results)
    events.to_csv(OUT / "event_level_results.csv", index=False)

    valid = events.loc[events["valid"].eq(True)].copy()
    windows = ["car_-1_1", "car_0_1", "car_0_2", "car_0_5"]

    summary_rows = []
    for window in windows:
        values = valid[window].dropna()
        if values.empty:
            continue
        t = ttest_1samp(values, 0.0)
        try:
            w = wilcoxon(values)
            wilcoxon_p = float(w.pvalue)
        except ValueError:
            wilcoxon_p = np.nan

        summary_rows.append(
            {
                "window": window,
                "n": len(values),
                "mean_car": values.mean(),
                "median_car": values.median(),
                "sd": values.std(ddof=1),
                "t_stat": float(t.statistic),
                "t_p": float(t.pvalue),
                "wilcoxon_p": wilcoxon_p,
                "positive_share": values.gt(0).mean(),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "car_summary.csv", index=False)

    timing_rows = []
    for window in windows:
        data = valid.dropna(subset=[window, "after_1630"]).copy()
        if len(data) < 15:
            continue

        fit = smf.ols(f"{window} ~ after_1630", data=data).fit(cov_type="HC1")
        timing_rows.append(
            {
                "window": window,
                "timing": "after_1630",
                "coef": fit.params.get("after_1630[T.True]", np.nan),
                "se": fit.bse.get("after_1630[T.True]", np.nan),
                "p": fit.pvalues.get("after_1630[T.True]", np.nan),
                "n": int(fit.nobs),
            }
        )

        fit2 = smf.ols(f"{window} ~ after_1600", data=data).fit(cov_type="HC1")
        timing_rows.append(
            {
                "window": window,
                "timing": "after_1600",
                "coef": fit2.params.get("after_1600[T.True]", np.nan),
                "se": fit2.bse.get("after_1600[T.True]", np.nan),
                "p": fit2.pvalues.get("after_1600[T.True]", np.nan),
                "n": int(fit2.nobs),
            }
        )

    timing = pd.DataFrame(timing_rows)
    timing.to_csv(OUT / "timing_car_models.csv", index=False)

    missing = sample.loc[sample["ticker"].isna(), ["cik", "company_name", "accession_no"]]
    missing.to_csv(OUT / "missing_tickers.csv", index=False)

    print("Cyber events:", len(sample))
    print("Mapped tickers:", sample["ticker"].notna().sum())
    print("Valid event studies:", len(valid))
    print(summary.to_string(index=False))
    print(timing.to_string(index=False))
    if not missing.empty:
        print("Missing tickers:")
        print(missing.to_string(index=False))


if __name__ == "__main__":
    main()
