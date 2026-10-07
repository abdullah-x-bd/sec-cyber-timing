import pandas as pd

from sec_cyber_timing.analysis import deadline_distribution, fit_timing_lpm
from sec_cyber_timing.config import ROOT


def main() -> None:
    data = pd.read_csv(
        ROOT / "data" / "processed" / "timing_analysis.csv",
        dtype={"cik": str},
    )

    results_dir = ROOT / "results" / "tables"
    results_dir.mkdir(parents=True, exist_ok=True)

    cyber = data.loc[data["is_item_105"].astype(str).str.lower().eq("true")].copy()
    distribution = deadline_distribution(cyber)
    distribution.to_csv(results_dir / "deadline_distribution.csv", index=False)

    rows = []
    for outcome in ["after_hours", "friday"]:
        result = fit_timing_lpm(data, outcome)
        rows.append(
            {
                "outcome": outcome,
                "item_105_coefficient": result.params.get("is_item_105"),
                "standard_error": result.bse.get("is_item_105"),
                "p_value": result.pvalues.get("is_item_105"),
                "n": int(result.nobs),
            }
        )

    pd.DataFrame(rows).to_csv(results_dir / "timing_models.csv", index=False)
    print(results_dir)


if __name__ == "__main__":
    main()
