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
    knowledge_date_c = first_existing(cyber, ["knowledge_date"])
    amendment_c = first_existing(cyber, ["is_amendment"])

    filings[accession_f] = filings[accession_f].astype(str)
    filings[cik_f] = filings[cik_f].astype(str).str.zfill(10)
    filings[filing_date_f] = pd.to_datetime(filings[filing_date_f], errors="coerce")
    filings[accepted_f] = pd.to_datetime(filings[accepted_f], errors="coerce", utc=True)

    cyber[accession_c] = cyber[accession_c].astype(str)
    cyber[cik_c] = cyber[cik_c].astype(str).str.zfill(10)
    cyber[knowledge_date_c] = pd.to_datetime(
        cyber[knowledge_date_c], errors="coerce", utc=True
    )
    cyber["knowledge_date_et"] = (
        cyber[knowledge_date_c]
        .dt.tz_convert("America/New_York")
        .dt.tz_localize(None)
    )

    start = pd.Timestamp("2024-06-15")
    end = pd.Timestamp("2026-09-30")

    cyber_primary = cyber.loc[
        ~cyber[amendment_c].astype(bool)
        & cyber["knowledge_date_et"].between(start, end + pd.Timedelta(days=1))
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
    items_col = next((c for c in ["items_raw", "items", "item_codes", "item"] if c in combined.columns), None)
    if items_col:
        combined["has_202"] = combined[items_col].astype(str).str.contains(
            r"(^|[,;\s])2\.02($|[,;\s])", regex=True
        )
    else:
        combined["has_202"] = False

    # Distance from each filing to the nearest cyber filing by the same issuer.
    cyber_dates = {
        cik: group[filing_date_f].dropna().tolist()
        for cik, group in cyber_filing_rows.groupby(cik_f)
    }

    def nearest_cyber_days(row: pd.Series) -> float:
        dates = cyber_dates.get(row[cik_f], [])
        if not dates or pd.isna(row[filing_date_f]):
            return np.nan
        return min(abs((row[filing_date_f] - value).days) for value in dates)

    combined["nearest_cyber_days"] = combined.apply(nearest_cyber_days, axis=1)

    # Clock-time bins describe submission timing independently of SEC dissemination.
    minute_of_day = (
        accepted_et.dt.hour * 60
        + accepted_et.dt.minute
        + accepted_et.dt.second / 60
    )
    combined["time_bin"] = pd.cut(
        minute_of_day,
        bins=[-np.inf, 9.5 * 60, 16 * 60, 16.5 * 60, np.inf],
        labels=[
            "pre_market_clock",
            "regular_clock",
            "first_30_postclose",
            "late_postclose",
        ],
        right=False,
    )

    combined.to_csv(OUT / "matched_firm_8k_sample.csv", index=False)

    sample_masks = {
        "all_controls": pd.Series(True, index=combined.index),
        "controls_ex_202": combined["is_cyber"].eq(1) | ~combined["has_202"],
        "controls_ex_202_exact": (
            (combined["is_cyber"].eq(1) | ~combined["has_202"])
            & ~combined["knowledge_estimated"].astype(bool)
        ),
        "within_365d_ex_202": (
            combined["is_cyber"].eq(1)
            | (
                ~combined["has_202"]
                & combined["nearest_cyber_days"].le(365)
            )
        ),
        "within_180d_ex_202": (
            combined["is_cyber"].eq(1)
            | (
                ~combined["has_202"]
                & combined["nearest_cyber_days"].le(180)
            )
        ),
        "within_90d_ex_202": (
            combined["is_cyber"].eq(1)
            | (
                ~combined["has_202"]
                & combined["nearest_cyber_days"].le(90)
            )
        ),
    }

    summary_rows = []
    for sample_name, mask in sample_masks.items():
        sample = combined.loc[mask].copy()
        for label, subset in [
            ("cyber", sample.loc[sample["is_cyber"].eq(1)]),
            ("controls", sample.loc[sample["is_cyber"].eq(0)]),
        ]:
            summary_rows.append(
                {
                    "sample": sample_name,
                    "group": label,
                    "n": len(subset),
                    "unique_firms": subset["cik_key"].nunique(),
                    "after_market_rate": subset["after_hours"].mean(),
                    "after_1600_rate": subset["after_1600"].mean(),
                    "after_1630_rate": subset["after_1630"].mean(),
                    "after_1700_rate": subset["after_1700"].mean(),
                    "friday_rate": subset["friday"].mean(),
                    "exact_timestamp_rate": (
                        ~subset["knowledge_estimated"].astype(bool)
                    ).mean(),
                }
            )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "group_summary.csv", index=False)

    time_bins = (
        combined.groupby(["is_cyber", "time_bin"], observed=True)
        .size()
        .rename("n")
        .reset_index()
    )
    time_bins["share_within_group"] = time_bins.groupby("is_cyber")["n"].transform(
        lambda values: values / values.sum()
    )
    time_bins.to_csv(OUT / "clock_time_bins.csv", index=False)

    year_summary = (
        combined.assign(year=combined[filing_date_f].dt.year)
        .groupby(["is_cyber", "year"], as_index=False)
        .agg(
            n=("after_1600", "size"),
            after_1600_rate=("after_1600", "mean"),
            after_1630_rate=("after_1630", "mean"),
            friday_rate=("friday", "mean"),
        )
    )
    year_summary.to_csv(OUT / "year_summary.csv", index=False)

    model_rows = []
    for sample_name, mask in sample_masks.items():
        sample = combined.loc[mask].copy()
        for outcome in [
            "after_hours",
            "after_1600",
            "after_1630",
            "after_1700",
            "friday",
        ]:
            data = sample.dropna(
                subset=[outcome, "is_cyber", "cik_key", "year_month"]
            ).copy()
            fit = smf.ols(
                f"{outcome} ~ is_cyber + C(cik_key) + C(year_month)",
                data=data,
            ).fit(cov_type="cluster", cov_kwds={"groups": data["cik_key"]})
            model_rows.append(
                {
                    "sample": sample_name,
                    "outcome": outcome,
                    "coef": fit.params.get("is_cyber", np.nan),
                    "se": fit.bse.get("is_cyber", np.nan),
                    "p": fit.pvalues.get("is_cyber", np.nan),
                    "n": int(fit.nobs),
                    "firms": int(data["cik_key"].nunique()),
                }
            )

    models = pd.DataFrame(model_rows)
    models.to_csv(OUT / "fixed_effect_models.csv", index=False)

    # Firm-level paired descriptive comparison.
    firm = (
        combined.groupby(["cik_key", "is_cyber"])
        .agg(
            n=("after_1600", "size"),
            after_1600=("after_1600", "mean"),
            after_1630=("after_1630", "mean"),
            friday=("friday", "mean"),
        )
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
