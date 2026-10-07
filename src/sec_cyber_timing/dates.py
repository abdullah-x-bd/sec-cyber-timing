from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)"
)
DATE = rf"{MONTH}\s+\d{{1,2}},\s+20\d{{2}}"

PATTERNS = [
    (
        rf"On\s+(?P<date>{DATE}),?\s+(?:the\s+)?(?:Company|company|registrant|we)\s+"
        rf"(?:determined|concluded)\s+(?:that\s+)?(?:the\s+)?(?:cybersecurity\s+)?"
        rf"incident\s+(?:was|is|to be)\s+material"
    ),
    (
        rf"(?:determined|concluded)\s+(?:that\s+)?(?:the\s+)?(?:cybersecurity\s+)?"
        rf"incident\s+(?:was|is|to be)\s+material\s+on\s+(?P<date>{DATE})"
    ),
    rf"materiality\s+determination\s+(?:was\s+)?made\s+on\s+(?P<date>{DATE})",
]

SEC_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())


@dataclass(frozen=True)
class DateCandidate:
    value: date
    pattern_index: int
    matched_text: str


def extract_materiality_date_candidates(text: str) -> list[DateCandidate]:
    candidates: list[DateCandidate] = []
    for pattern_index, pattern in enumerate(PATTERNS):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            parsed = pd.to_datetime(match.group("date"), errors="coerce")
            if pd.isna(parsed):
                continue
            candidates.append(
                DateCandidate(
                    value=parsed.date(),
                    pattern_index=pattern_index,
                    matched_text=match.group(0),
                )
            )
    unique: dict[date, DateCandidate] = {}
    for candidate in candidates:
        unique.setdefault(candidate.value, candidate)
    return list(unique.values())


def business_days_after(start: date, end: date) -> int:
    if end < start:
        return -business_days_after(end, start)
    if end == start:
        return 0
    days = pd.date_range(
        pd.Timestamp(start) + SEC_BUSINESS_DAY,
        pd.Timestamp(end),
        freq=SEC_BUSINESS_DAY,
    )
    return len(days)
