import pandas as pd

from sec_cyber_timing.config import ROOT
from sec_cyber_timing.dates import extract_materiality_date_candidates
from sec_cyber_timing.filings import html_to_text


def main() -> None:
    sample = pd.read_csv(
        ROOT / "data" / "interim" / "item_105_filings.csv",
        dtype={"cik": str},
    )

    records = []
    filing_dir = ROOT / "data" / "raw" / "sec" / "filings"

    for _, row in sample.iterrows():
        accession = str(row["accessionNumber"])
        path = filing_dir / f"{accession}.html"
        if not path.exists():
            continue

        text = html_to_text(path)
        candidates = extract_materiality_date_candidates(text)

        if not candidates:
            records.append(
                {
                    "accessionNumber": accession,
                    "candidate_date": None,
                    "pattern_index": None,
                    "matched_text": None,
                }
            )
            continue

        for candidate in candidates:
            records.append(
                {
                    "accessionNumber": accession,
                    "candidate_date": candidate.value.isoformat(),
                    "pattern_index": candidate.pattern_index,
                    "matched_text": candidate.matched_text,
                }
            )

    output = pd.DataFrame(records)
    output.to_csv(
        ROOT / "data" / "interim" / "materiality_date_candidates.csv",
        index=False,
    )
    print(f"Wrote {len(output):,} candidate rows.")


if __name__ == "__main__":
    main()
