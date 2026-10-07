from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf


def download_adjusted_prices(
    tickers: list[str],
    start: str,
    end: str,
    cache_path: Path | None = None,
) -> pd.DataFrame:
    cleaned = sorted({ticker for ticker in tickers if isinstance(ticker, str) and ticker})
    if not cleaned:
        return pd.DataFrame()

    data = yf.download(
        cleaned,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )

    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"].copy()
    else:
        prices = data[["Close"]].rename(columns={"Close": cleaned[0]})

    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        prices.to_csv(cache_path, index_label="date")
    return prices


def first_market_session_for_filing(
    acceptance_et: pd.Timestamp,
    market_close_hour: int = 16,
) -> pd.Timestamp:
    if pd.isna(acceptance_et):
        return pd.NaT

    calendar = mcal.get_calendar("NYSE")
    filing_date = pd.Timestamp(acceptance_et.date())
    schedule = calendar.schedule(
        start_date=filing_date - pd.Timedelta(days=3),
        end_date=filing_date + pd.Timedelta(days=7),
    )
    sessions = pd.DatetimeIndex(schedule.index)

    if filing_date in sessions and acceptance_et.hour < market_close_hour:
        return filing_date

    later = sessions[sessions > filing_date]
    return later[0] if len(later) else pd.NaT
