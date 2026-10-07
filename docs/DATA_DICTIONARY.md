# Data dictionary

## Filing identifiers

| Variable | Description |
| --- | --- |
| accessionNumber | SEC accession number for the filing |
| cik | SEC Central Index Key, zero-padded to ten digits |
| company_name | Registrant name from SEC submissions data |
| ticker | First reported ticker from SEC submissions metadata, subject to manual override |
| form | SEC form type |
| items | Form 8-K item string reported by EDGAR |
| is_item_105 | True when Item 1.05 appears in the EDGAR item string |
| filingDate | Official SEC filing date |
| acceptanceDateTime | EDGAR acceptance timestamp |
| primaryDocument | Primary filing document filename |

## Reviewed chronology

| Variable | Description |
| --- | --- |
| review_materiality_date | Human-verified date on which the registrant says it determined the incident was material |
| incident_discovery_date | Human-reviewed incident discovery date when clearly disclosed |
| include_deadline_analysis | Manual inclusion flag for the four-business-day analysis |
| review_notes | Short provenance or exclusion note |
| delay_business_days | Business days between reviewed materiality determination and official filing date |

## Timing outcomes

| Variable | Description |
| --- | --- |
| acceptance_et | Acceptance timestamp normalized to America/New_York |
| after_hours | Acceptance at or after the configured market-close threshold |
| friday | Official filing date is Friday |
| year_month | Calendar-month fixed-effect key |

## Event study

| Variable | Description |
| --- | --- |
| event_date | First trading session in which the filing could be incorporated into prices |
| alpha | Estimated market-model intercept |
| beta | Estimated market-model loading on the benchmark |
| car_-1_1 | Cumulative abnormal return from day -1 through +1 |
| car_0_1 | Cumulative abnormal return from day 0 through +1 |
| car_0_2 | Cumulative abnormal return from day 0 through +2 |
| car_0_5 | Cumulative abnormal return from day 0 through +5 |
