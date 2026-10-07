import pandas as pd

from sec_cyber_timing.config import ROOT


def main() -> None:
    sample = pd.read_csv(
        ROOT / "data" / "interim" / "item_105_filings.csv",
        dtype={"cik": str},
    )
    candidates_path = ROOT / "data" / "interim" / "materiality_date_candidates.csv"
    candidates = pd.read_csv(candidates_path) if candidates_path.exists() else pd.DataFrame()

    if not candidates.empty:
        first_candidate = (
            candidates.dropna(subset=["candidate_date"])
            .drop_duplicates("accessionNumber")
            [["accessionNumber", "candidate_date", "matched_text"]]
        )
        queue = sample.merge(first_candidate, on="accessionNumber", how="left")
    else:
        queue = sample.copy()
        queue["candidate_date"] = pd.NA
        queue["matched_text"] = pd.NA

    queue["review_materiality_date"] = ""
    queue["include_deadline_analysis"] = ""
    queue["incident_discovery_date"] = ""
    queue["review_notes"] = ""

    columns = [
        "accessionNumber",
        "cik",
        "company_name",
        "filingDate",
        "candidate_date",
        "matched_text",
        "review_materiality_date",
        "include_deadline_analysis",
        "incident_discovery_date",
        "review_notes",
    ]
    output = ROOT / "data" / "interim" / "validation_queue.csv"
    queue[columns].to_csv(output, index=False)
    print(output)


if __name__ == "__main__":
    main()
