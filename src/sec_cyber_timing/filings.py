from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


def item_contains(value: object, item: str) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    tokens = re.split(r"[,;\s]+", str(value).strip())
    return item in {token for token in tokens if token}


def build_filing_universe(records: list[dict], start: str, end: str) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame

    frame["filingDate"] = pd.to_datetime(frame["filingDate"], errors="coerce")
    frame["acceptanceDateTime"] = pd.to_datetime(
        frame.get("acceptanceDateTime"), errors="coerce"
    )

    mask = (
        frame["form"].isin(["8-K", "8-K/A"])
        & frame["filingDate"].between(pd.Timestamp(start), pd.Timestamp(end))
    )
    frame = frame.loc[mask].copy()
    frame["is_item_105"] = frame["items"].map(lambda value: item_contains(value, "1.05"))
    frame["ticker"] = frame["tickers"].map(
        lambda values: values[0] if isinstance(values, list) and values else None
    )
    return frame.sort_values(["filingDate", "acceptanceDateTime", "cik"]).reset_index(drop=True)


def filing_document_url(row: pd.Series) -> str:
    accession = str(row["accessionNumber"]).replace("-", "")
    cik = str(int(str(row["cik"])))
    primary_document = row["primaryDocument"]
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_document}"


def html_to_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    return "\n".join(line.strip() for line in soup.stripped_strings)
