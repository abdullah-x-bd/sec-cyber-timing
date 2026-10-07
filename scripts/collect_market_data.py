from datetime import timedelta

import pandas as pd

from sec_cyber_timing.config import ROOT, load_config
from sec_cyber_timing.market import download_adjusted_prices


def main() -> None:
    config = load_config()
    study = config["study"]
    event_config = config["event_study"]

    sample = pd.read_csv(
        ROOT / "data" / "processed" / "cyber_filings.csv",
        dtype={"cik": str},
    )
    tickers = sample["ticker"].dropna().astype(str).tolist()
    tickers.append(event_config["benchmark_ticker"])

    start = pd.Timestamp(study["collection_start"]) - timedelta(days=240)
    end = pd.Timestamp(study["end_date"]) + timedelta(days=15)

    output = ROOT / "data" / "raw" / "market" / "adjusted_close.csv"
    prices = download_adjusted_prices(
        tickers=tickers,
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        cache_path=output,
    )
    print(f"Downloaded {prices.shape[1]} price series to {output}.")


if __name__ == "__main__":
    main()
