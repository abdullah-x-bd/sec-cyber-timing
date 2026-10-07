# SEC Cyber Disclosure Timing

This repository contains the code and data pipeline for a working paper on the timing of mandatory cybersecurity disclosures by U.S. public companies.

The project studies a simple question: when firms have up to four business days after determining that a cybersecurity incident is material to file an Item 1.05 Form 8-K, how do they use that disclosure window?

The empirical design focuses on three outcomes:

1. whether material cyber filings bunch near the end of the permitted disclosure window;
2. whether firms are more likely to file cyber disclosures after market close or on Fridays than their own non-cyber Form 8-K filings; and
3. whether disclosure delay and filing timing are associated with differences in the subsequent market reaction.

The study is designed around public, reproducible data. SEC EDGAR provides filing metadata and acceptance timestamps. Filing documents provide incident and materiality information. Daily market data are used for the event-study component.

## Research design

The primary sample consists of Form 8-K filings under Item 1.05 after the SEC cybersecurity incident disclosure rule became effective.

The main timing variables are:

- EDGAR acceptance date and time
- stated materiality determination date, when disclosed
- business-day distance from materiality determination to filing
- after-hours filing indicator
- Friday filing indicator
- final-permitted-day indicator

The main comparison sample consists of other Form 8-K filings by the same issuers during the study period. This allows the analysis to distinguish cyber-specific disclosure timing from a firm's ordinary filing habits.

Market-response analysis is conducted separately from the timing analysis. The event date is aligned to the first trading session in which the filing could reasonably be incorporated into prices. Filings accepted after market close are therefore assigned to the next trading session for the primary event-time specification.

The initial analysis protocol is in `docs/PROTOCOL.md`. Variable definitions are in `docs/DATA_DICTIONARY.md`.

## Study period

The collection window begins on 18 December 2023, when most registrants became subject to Item 1.05. The primary deadline analysis begins on 15 June 2024, by which point the delayed compliance period for smaller reporting companies had ended.

The frozen end date is 30 September 2026. Study dates and analysis settings are controlled in `config/study.yaml`.

## Repository structure

```
config/             study parameters and frozen settings
data/
  raw/              downloaded source data, not committed by default
  interim/          parser outputs and validation queues
  manual/           small human-reviewed annotation files
  processed/        final analysis-ready datasets
docs/               protocol and variable definitions
results/
  figures/          generated figures
  tables/           generated tables
src/sec_cyber_timing/
                    reusable collection and analysis package
scripts/            command-line entry points
tests/              unit tests
```

## Reproducibility

The workflow keeps source collection, parsing, manual validation, sample construction, and statistical analysis separate.

Raw source files are cached locally. Manual annotations are stored as small version-controlled tables rather than silently edited into processed data. Analysis-ready files are generated from source data and annotations.

The SEC collector uses the Commission's public bulk submissions archive, then downloads only the filing documents required for the cyber sample. It requires a descriptive user agent and uses conservative request throttling. No SEC API key is required.

## Workflow

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Add a descriptive SEC_USER_AGENT before making SEC requests.

# 1. Build the SEC filing universe.
python scripts/collect_sec.py
python scripts/build_filing_sample.py

# 2. Cache Item 1.05 filings and extract candidate chronology.
python scripts/fetch_filing_docs.py
python scripts/extract_materiality_dates.py
python scripts/build_validation_queue.py

# 3. Review the validation queue and copy reviewed decisions into
#    data/manual/materiality_annotations.csv.

# 4. Build the frozen analysis datasets.
python scripts/build_analysis_data.py

# 5. Run the disclosure-timing analysis.
python scripts/run_timing_analysis.py

# 6. Download public market data and run the event study.
python scripts/collect_market_data.py
python scripts/run_event_study.py

pytest
```

## Manual review

Automated extraction is used to find candidate materiality-determination dates, not to silently decide them.

Each date used in the deadline analysis is checked against the source filing and recorded in `data/manual/materiality_annotations.csv`. Ticker corrections and market-data exclusions are recorded in `data/manual/issuer_overrides.csv`.

This keeps the small amount of judgment in the study visible and auditable.

## Current status

The repository is in the protocol and data-pipeline stage. No confirmatory results have been inspected.

The primary outcomes, exclusions, event-time rules, and baseline specifications are recorded before the final analysis dataset is examined.

## Working paper

**Bad News on the Clock: Strategic Timing of Mandatory Cybersecurity Disclosures**

The title remains provisional until the filing sample is fully audited.
