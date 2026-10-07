import pandas as pd

from sec_cyber_timing.filings import item_contains
from sec_cyber_timing.timing import add_timing_variables


def test_item_contains_exact_item():
    assert item_contains("1.05,9.01", "1.05")
    assert item_contains("1.05 9.01", "1.05")
    assert not item_contains("1.01,5.02", "1.05")


def test_after_hours_and_friday():
    frame = pd.DataFrame(
        {
            "acceptanceDateTime": ["2026-09-18 16:15:00"],
            "filingDate": ["2026-09-18"],
        }
    )
    out = add_timing_variables(frame)
    assert bool(out.loc[0, "after_hours"]) is True
    assert bool(out.loc[0, "friday"]) is True
