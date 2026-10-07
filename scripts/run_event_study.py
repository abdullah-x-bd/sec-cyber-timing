import pandas as pd

from sec_cyber_timing.config import ROOT, load_config
from sec_cyber_timing.event_study import market_model_event
from sec_cyber_timing.market import first_market_session_for_filing
from sec_cyber_timing.timing import normalize_acceptance_datetime


def main() -> None:
    config = load_config()
    event_config = config["event_study"]

    sample = pd.read_csv(
        ROOT / "data" / "processed" / "cyber_filings.csv",
        dtype={"cik": str},
    )
    prices = pd.read_csv(
        ROOT / "data" / "raw" / "market" / "adjusted_close.csv",
        index_col="date",
        parse_dates=True,
    )
    overrides = pd.read_csv(
        ROOT / "data" / "manual" / "issuer_overrides.csv",
        dtype={"cik": str},
    )

    if not overrides.empty:
        overrides = overrides.dropna(subset=["cik"]).drop_duplicates("cik")
        override_map = overrides.set_index("cik")["ticker"].dropna().to_dict()
        exclude_map = (
            overrides.set_index("cik")["exclude_from_market_analysis"]
            .fillna(False)
            .astype(str)
            .str.lower()
            .isin({"1", "true", "yes", "y"})
            .to_dict()
        )
    else:
        override_map = {}
        exclude_map = {}

    benchmark = event_config["benchmark_ticker"]
    if benchmark not in prices:
        raise KeyError(f"Benchmark {benchmark} not found in market data.")

    windows = [tuple(window) for window in event_config["event_windows"]]
    results = []

    for _, row in sample.iterrows():
        cik = str(row["cik"])
        if exclude_map.get(cik, False):
            continue

        ticker = override_map.get(cik, row.get("ticker"))
        if not isinstance(ticker, str) or ticker not in prices:
            results.append(
                {
                    "accessionNumber": row["accessionNumber"],
                    "cik": cik,
                    "ticker": ticker,
                    "valid": False,
                    "reason": "ticker_missing",
                }
            )
            continue

        acceptance = normalize_acceptance_datetime(row["acceptanceDateTime"])
        event_date = first_market_session_for_filing(acceptance)

        result = market_model_event(
            asset_prices=prices[ticker],
            benchmark_prices=prices[benchmark],
            event_date=event_date,
            estimation_start=int(event_config["estimation_window_start"]),
            estimation_end=int(event_config["estimation_window_end"]),
            event_windows=windows,
        )
        result.update(
            {
                "accessionNumber": row["accessionNumber"],
                "cik": cik,
                "ticker": ticker,
                "acceptance_et": acceptance,
            }
        )
        results.append(result)

    output = pd.DataFrame(results)
    destination = ROOT / "results" / "tables" / "event_study.csv"
    output.to_csv(destination, index=False)
    print(destination)


if __name__ == "__main__":
    main()
