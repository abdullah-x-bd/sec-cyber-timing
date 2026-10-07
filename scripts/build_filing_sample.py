from sec_cyber_timing.config import ROOT, load_config
from sec_cyber_timing.filings import build_filing_universe
from sec_cyber_timing.sec import iter_submission_records


def main() -> None:
    config = load_config()
    study = config["study"]

    source = ROOT / "data" / "raw" / "sec" / "submissions.zip"
    if not source.exists():
        raise FileNotFoundError("Run scripts/collect_sec.py first.")

    records = list(iter_submission_records(source))
    universe = build_filing_universe(
        records,
        start=study["collection_start"],
        end=study["end_date"],
    )

    output_dir = ROOT / "data" / "interim"
    output_dir.mkdir(parents=True, exist_ok=True)

    universe.to_csv(output_dir / "filing_universe.csv", index=False)

    cyber = universe.loc[universe["is_item_105"]].copy()
    cyber.to_csv(output_dir / "item_105_filings.csv", index=False)

    cyber_ciks = set(cyber["cik"].astype(str))
    controls = universe.loc[
        universe["cik"].astype(str).isin(cyber_ciks) & ~universe["is_item_105"]
    ].copy()
    controls.to_csv(output_dir / "matched_firm_8k_controls.csv", index=False)

    print(f"8-K universe: {len(universe):,}")
    print(f"Item 1.05 filings: {len(cyber):,}")
    print(f"Matched-firm control filings: {len(controls):,}")


if __name__ == "__main__":
    main()
