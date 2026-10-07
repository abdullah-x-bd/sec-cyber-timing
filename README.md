# SEC Cyber Disclosure Timing

This repository contains the code and data pipeline for a working paper on the timing of mandatory cybersecurity disclosures by U.S. public companies.

The project studies a simple question: when firms have up to four business days after determining that a cybersecurity incident is material to file an Item 1.05 Form 8-K, how do they use that disclosure window?

The empirical design focuses on three outcomes:

1. whether material cyber filings bunch near the end of the permitted disclosure window;
2. whether firms are more likely to file cyber disclosures after market close or on Fridays than their own non-cyber Form 8-K filings; and
3. whether disclosure delay and filing timing are associated with differences in the subsequent market reaction.

The study is designed around public, reproducible data. SEC EDGAR provides filing metadata and acceptance timestamps. Filing documents provide incident and materiality information. Daily market data and standard factor returns are used for the event-study component.

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

## Study period

The collection window begins on 18 December 2023, when most registrants became subject to Item 1.05. Smaller reporting companies received a later compliance date and are handled explicitly in the sample construction rather than assumed to be subject to the rule from the first date.

The end date is controlled in `config/study.yaml` so the study can be frozen reproducibly.

## Repository structure

```
config/             study parameters and manually frozen settings
data/
  raw/              downloaded source data, not committed by default
  interim/          parser outputs and validation queues
  manual/           small human-reviewed annotation files
  processed/        final analysis-ready datasets
docs/               protocol, variable definitions, and research notes
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

Raw source files are cached locally with provenance metadata. Manual annotations are stored as small version-controlled tables rather than silently edited into processed data. Analysis-ready files are generated from source data and annotations.

The SEC collector requires a descriptive user agent and uses conservative request throttling. No API key is required for the public EDGAR data used here.

## Planned workflow

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Add a descriptive SEC_USER_AGENT before making SEC requests.

python scripts/collect_sec.py
python scripts/build_filing_sample.py
python scripts/extract_materiality_dates.py
python scripts/build_validation_queue.py

# After reviewing the small annotation queue:
python scripts/build_analysis_data.py
python scripts/run_timing_analysis.py
python scripts/run_event_study.py

pytest
```

## Current status

The repository is in the protocol and data-pipeline stage. No confirmatory results have been inspected yet.

The design, outcome definitions, exclusions, and event-study conventions will be frozen before the final analysis dataset is examined.

## Working paper

**Bad News on the Clock: Strategic Timing of Mandatory Cybersecurity Disclosures**

The title and specification remain provisional until the sample is fully audited.
