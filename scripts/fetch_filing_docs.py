import pandas as pd

from sec_cyber_timing.config import ROOT, load_config
from sec_cyber_timing.filings import filing_document_url
from sec_cyber_timing.sec import SecClient


def main() -> None:
    config = load_config()
    sec_config = config["sec"]
    sample = pd.read_csv(
        ROOT / "data" / "interim" / "item_105_filings.csv",
        dtype={"cik": str},
    )

    client = SecClient.from_env(
        max_requests_per_second=float(sec_config["max_requests_per_second"])
    )
    output_dir = ROOT / "data" / "raw" / "sec" / "filings"
    output_dir.mkdir(parents=True, exist_ok=True)

    for _, row in sample.iterrows():
        accession = str(row["accessionNumber"])
        destination = output_dir / f"{accession}.html"
        if destination.exists():
            continue
        response = client.get(filing_document_url(row))
        destination.write_bytes(response.content)

    print(f"Cached {len(sample):,} Item 1.05 filing documents.")


if __name__ == "__main__":
    main()
