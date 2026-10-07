from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


ROOT = Path(__file__).resolve().parents[1]
HF_ROOT = Path("/tmp/sec-8k-events")
OUT = ROOT / "results" / "public_control"
OUT.mkdir(parents=True, exist_ok=True)


def load_parts(name: str) -> pd.DataFrame:
    files = sorted((HF_ROOT / "data" / name).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for {name}")
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)


def first_existing(frame: pd.DataFrame, names: list[str]) -> str:
    for name in names:
        if name in frame.columns:
            return name
    raise KeyError(f"None of {names} found. Columns: {list(frame.columns)}")


def as_bool_original(form_value: object) -> bool:
    value = str(form_value).upper().strip()
    return value == "8-K"


def main() -> None:
    filings = load_parts("filings")
    cyber = load_parts("cyber_events")

    schema = {
        "filings_rows": len(filings),
        "cyber_rows": len(cyber),
        "filings_columns": list(filings.columns),
        "cyber_columns": list(cyber.columns),
    }
    (OUT / "schema.json").write_text(json.dumps(schema, indent=2, default=str))

    accession_f = first_existing(filings, ["accession_no", "accessionNumber", "accession"])
    cik_f = first_existing(filings, ["cik", "entity_cik"])
    filing_date_f = first_existing(filings, ["filing_date", "filingDate"])
    accepted_f = first_existing(filings, ["accepted_at", "acceptance_datetime", "acceptanceDateTime"])
    form_f = first_existing(filings, ["form", "form_type", "formType"])
    session_f = first_existing(filings, ["market_session"])

    accession_c = first_existing(cyber, ["accession_no", "accessionNumber", "accession"])
    cik_c = first_existing(cyber, ["cik", "entity_cik"])
    filing_date_c = first_existing(cyber, ["filing_date", "filingDate"])
    form_c = first_existing(cyber, ["form", "form_type", "formType"])

    filings[accession_f] = filings[accession_f].astype(str)
    filings[cik_f] = filings[cik_f].astype(str).str.zfill(10)
    filings[filing_date_f] = pd.to_datetime(filings[filing_date_f], errors="coerce")
    filings[accepted_f] = pd.to_datetime(filings[accepted_f], errors="coerce", utc=True)

    cyber[accession_c] = cyber[accession_c].astype(str)
    cyber[cik_c] = cyber[cik_c].astype(str).str.zfill(10)
    cyber[filing_date_c] = pd.to_datetime(cyber[filing_date_c], errors="coerce")

    start = pd.Timestamp("2024-06-15")
    end = pd.Timestamp("2026-09-30")

    cyber_primary = cyber.loc[
        cyber[form_c].map(as_bool_original)
        & cyber[filing_date_c].between(start, end)
    ].copy()
    cyber_primary = cyber_primary.drop_duplicates(accession_c)

    cyber_accessions = set(cyber_primary[accession_c])
    cyber_ciks = set(cyber_primary[cik_c])

    controls = filings.loc[
        filings[cik_f].isin(cyber_ciks)
        & filings[filing_date_f].between(start, end)
        & filings[form_f].map(as_bool_original)
        & ~filings[accession_f].isin(cyber_accessions)
    ].copy()

    cyber_filing_rows = filings.loc[filings[accession_f].isin(cyber_accessions)].copy()

    combined = pd.concat(
        [
            cyber_filing_rows.assign(is_cyber=1),
            controls.assign(is_cyber=0),
        ],
        ignore_index=True,
    )

    combined["after_hours"] = combined[session_f].astype(str).eq("after_market").astype(int)
    combined["friday"] = combined[filing_date_f].dt.dayofweek.eq(4).astype(int)
    combined["year_month"] = combined[filing_date_f].dt.to_period("M").astype(str)
    combined["cik_key"] = combined[cik_f].astype(str)

    # Standard 4pm clock indicator, distinct from the exchange-calendar market_session field.
    accepted_et = combined[accepted_f].dt.tz_convert("America/New_York")
    combined["after_1600"] = (
        (accepted_et.dt.hour > 16)
        | ((accepted_et.dt.hour == 16) & (accepted_et.dt.minute >= 0))
    ).astype(int)
    combined["after_1630"] = (
        (accepted_et.dt.hour > 16)
        | ((accepted_et.dt.hour == 16) & (accepted_et.dt.minute >= 30))
    ).astype(int)
    combined["after_1700"] = (accepted_et.dt.hour >= 17).astype(int)

    # Identify 2.02 controls if a usable items field is present.
    items_col = next((c for c in ["items", "item_codes", "item"] if c in combined.columns), None)
    if items_col:
        combined["has_202"] = combined[items_col].astype(str).str.contains(
            r"(^|[,;\s])2\.02($|[,;\s])", regex=True
        )
    else:
        combined["has_202"] = False

    combined.to_csv(OUT / "matched_firm_8k_sample.csv", index=False)

    summary_rows = []
    for label, subset in [
        ("cyber", combined.loc[combined.is_cyber.eq(1)]),
        ("controls", combined.loc[combined.is_cyber.eq(0)]),
        ("controls_ex_202", combined.loc[combined.is_cyber.eq(0) & ~combined.has_202]),
    ]:
        summary_rows.append(
            {
                "group": label,
                "n": len(subset),
                "unique_firms": subset["cik_key"].nunique(),
                "after_market_rate": subset["after_hours"].mean(),
                "after_1600_rate": subset["after_1600"].mean(),
                "after_1630_rate": subset["after_1630"].mean(),
                "after_1700_rate": subset["after_1700"].mean(),
                "friday_rate": subset["friday"].mean(),
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "group_summary.csv", index=False)

    model_rows = []
    for outcome in ["after_hours", "after_1600", "friday"]:
        data = combined.dropna(subset=[outcome, "is_cyber", "cik_key", "year_month"]).copy()
        fit = smf.ols(
            f"{outcome} ~ is_cyber + C(cik_key) + C(year_month)",
            data=data,
        ).fit(cov_type="cluster", cov_kwds={"groups": data["cik_key"]})
        model_rows.append(
            {
                "sample": "all_controls",
                "outcome": outcome,
                "coef": fit.params.get("is_cyber", np.nan),
                "se": fit.bse.get("is_cyber", np.nan),
                "p": fit.pvalues.get("is_cyber", np.nan),
                "n": int(fit.nobs),
                "firms": int(data["cik_key"].nunique()),
            }
        )

        no_earn = data.loc[(data.is_cyber.eq(1)) | (~data.has_202)].copy()
        fit2 = smf.ols(
            f"{outcome} ~ is_cyber + C(cik_key) + C(year_month)",
            data=no_earn,
        ).fit(cov_type="cluster", cov_kwds={"groups": no_earn["cik_key"]})
        model_rows.append(
            {
                "sample": "controls_ex_202",
                "outcome": outcome,
                "coef": fit2.params.get("is_cyber", np.nan),
                "se": fit2.bse.get("is_cyber", np.nan),
                "p": fit2.pvalues.get("is_cyber", np.nan),
                "n": int(fit2.nobs),
                "firms": int(no_earn["cik_key"].nunique()),
            }
        )

    pd.DataFrame(model_rows).to_csv(OUT / "fixed_effect_models.csv", index=False)

    # Firm-level paired descriptive comparison.
    firm = (
        combined.groupby(["cik_key", "is_cyber"])
        .agg(n=("after_hours", "size"), after_hours=("after_hours", "mean"), friday=("friday", "mean"))
        .reset_index()
        .pivot(index="cik_key", columns="is_cyber")
    )
    firm.to_csv(OUT / "firm_level_rates.csv")

    discovery = {
        "cyber_primary_rows": len(cyber_primary),
        "cyber_primary_firms": int(cyber_primary[cik_c].nunique()),
        "cyber_rows_matched_to_filings": len(cyber_filing_rows),
        "control_rows": len(controls),
        "control_firms": int(controls[cik_f].nunique()),
    }
    (OUT / "discovery.json").write_text(json.dumps(discovery, indent=2))

    print(json.dumps(discovery, indent=2))
    print(summary.to_string(index=False))
    print(pd.DataFrame(model_rows).to_string(index=False))


if __name__ == "__main__":
    main()
