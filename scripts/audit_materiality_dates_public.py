from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from sec_cyber_timing.dates import extract_materiality_date_candidates


ROOT = Path(__file__).resolve().parents[1]
HF_ROOT = Path("/tmp/sec-8k-events")
OUT = ROOT / "results" / "materiality_audit"
OUT.mkdir(parents=True, exist_ok=True)

MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)"
)
DATE_RE = re.compile(rf"{MONTH}\s+\d{{1,2}},\s+20\d{{2}}", re.IGNORECASE)


def load_cyber() -> pd.DataFrame:
    paths = sorted((HF_ROOT / "data" / "cyber_events").glob("*.parquet"))
    return pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True)


def evidence_contexts(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []

    sentence_like = re.split(r"(?<=[.!?;])\s+", text)
    contexts = []
    for index, sentence in enumerate(sentence_like):
        lower = sentence.lower()
        if (
            "material" in lower
            and (
                "determin" in lower
                or "conclud" in lower
                or "reportable" in lower
                or "materiality" in lower
            )
        ):
            left = max(0, index - 1)
            right = min(len(sentence_like), index + 2)
            contexts.append(" ".join(sentence_like[left:right])[:1600])

    # Deduplicate while retaining order.
    return list(dict.fromkeys(contexts))


def main() -> None:
    cyber = load_cyber()
    cyber["knowledge_date"] = pd.to_datetime(
        cyber["knowledge_date"], errors="coerce", utc=True
    )
    cyber["knowledge_et"] = cyber["knowledge_date"].dt.tz_convert("America/New_York")

    sample = cyber.loc[
        ~cyber["is_amendment"].astype(bool)
        & cyber["knowledge_et"].dt.year.eq(2026)
        & cyber["knowledge_et"].dt.date.le(pd.Timestamp("2026-09-30").date())
    ].copy()
    sample = sample.drop_duplicates("accession_no")

    rows = []
    for _, row in sample.iterrows():
        text = row.get("item_text")
        text = "" if pd.isna(text) else str(text)

        parser_candidates = extract_materiality_date_candidates(text)
        contexts = evidence_contexts(text)
        context_text = " || ".join(contexts)
        context_dates = list(dict.fromkeys(DATE_RE.findall(context_text)))

        rows.append(
            {
                "accession_no": row["accession_no"],
                "cik": row["cik"],
                "company_name": row["company_name"],
                "knowledge_date": row["knowledge_date"],
                "has_item_text": bool(text.strip()),
                "parser_candidate_dates": "|".join(
                    candidate.value.isoformat() for candidate in parser_candidates
                ),
                "context_dates": "|".join(context_dates),
                "evidence_context": context_text,
                "manual_materiality_date": "",
                "manual_include": "",
                "manual_note": "",
            }
        )

    audit = pd.DataFrame(rows).sort_values("knowledge_date")
    audit.to_csv(OUT / "materiality_audit_2026.csv", index=False)

    print("2026 original Item 1.05 filings:", len(audit))
    print("With item text:", int(audit["has_item_text"].sum()))
    print(
        "With strict parser candidate:",
        int(audit["parser_candidate_dates"].astype(bool).sum()),
    )
    print(
        "With dated materiality context:",
        int(audit["context_dates"].astype(bool).sum()),
    )
    print(
        audit[
            [
                "company_name",
                "knowledge_date",
                "parser_candidate_dates",
                "context_dates",
                "evidence_context",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
