from datetime import date

from sec_cyber_timing.dates import (
    business_days_after,
    extract_materiality_date_candidates,
)


def test_extract_materiality_date():
    text = (
        "On March 4, 2025, the Company determined that the cybersecurity "
        "incident was material."
    )
    candidates = extract_materiality_date_candidates(text)
    assert len(candidates) == 1
    assert candidates[0].value == date(2025, 3, 4)


def test_business_days_same_day():
    assert business_days_after(date(2025, 3, 3), date(2025, 3, 3)) == 0


def test_business_days_skip_weekend():
    assert business_days_after(date(2025, 3, 3), date(2025, 3, 7)) == 4
    assert business_days_after(date(2025, 3, 7), date(2025, 3, 10)) == 1
