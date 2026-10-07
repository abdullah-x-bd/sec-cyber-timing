import pandas as pd

from sec_cyber_timing.config import ROOT, load_config
from sec_cyber_timing.dates import business_days_after
from sec_cyber_timing.timing import add_timing_variables


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main() -> None:
    config = load_config()
    cyber = pd.read_csv(
        ROOT / "data" / "interim" / "item_105_filings.csv",
        dtype={"cik": str},
    )
    controls = pd.read_csv(
        ROOT / "data" / "interim" / "matched_firm_8k_controls.csv",
        dtype={"cik": str},
    )

    annotations_path = ROOT / "data" / "manual" / "materiality_annotations.csv"
    annotations = pd.read_csv(annotations_path, dtype={"cik": str})
    annotations = annotations.loc[annotations["accessionNumber"].notna()].copy()

    if not annotations.empty:
        cyber = cyber.merge(
            annotations[
                [
                    "accessionNumber",
                    "review_materiality_date",
                    "include_deadline_analysis",
                    "incident_discovery_date",
                    "review_notes",
                ]
            ],
            on="accessionNumber",
            how="left",
        )
    else:
        cyber["review_materiality_date"] = pd.NA
        cyber["include_deadline_analysis"] = pd.NA
        cyber["incident_discovery_date"] = pd.NA
        cyber["review_notes"] = pd.NA

    cyber["materiality_date"] = pd.to_datetime(
        cyber["review_materiality_date"], errors="coerce"
    ).dt.date
    cyber["filing_date"] = pd.to_datetime(cyber["filingDate"], errors="coerce").dt.date
    cyber["deadline_review_included"] = cyber["include_deadline_analysis"].map(_truthy)
    cyber["delay_business_days"] = cyber.apply(
        lambda row: business_days_after(row["materiality_date"], row["filing_date"])
        if row["deadline_review_included"] and pd.notna(row["materiality_date"])
        else pd.NA,
        axis=1,
    )

    combined = pd.concat([cyber, controls], ignore_index=True, sort=False)
    combined = add_timing_variables(
        combined,
        market_close=config["timing"]["market_close"],
    )

    processed = ROOT / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    cyber.to_csv(processed / "cyber_filings.csv", index=False)
    combined.to_csv(processed / "timing_analysis.csv", index=False)
    print(processed)


if __name__ == "__main__":
    main()
