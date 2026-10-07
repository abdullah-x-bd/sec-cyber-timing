# Analysis protocol

## Research question

The study asks how U.S. public companies use the disclosure discretion created by the SEC rule requiring material cybersecurity incidents to be reported on Form 8-K under Item 1.05 within four business days after the company determines that the incident is material.

The paper is about observable disclosure timing. It does not treat delay, after-hours filing, or Friday filing as proof of concealment.

## Study period

Collection begins on 18 December 2023, the initial compliance date for most registrants.

The primary deadline analysis begins on 15 June 2024, when the delayed compliance period for smaller reporting companies had ended. This avoids requiring a firm-by-firm smaller-reporting-company classification for the main deadline specification.

The frozen end date is 30 September 2026. This leaves enough post-event trading sessions for the event-study windows.

## Samples

### Cyber sample

Form 8-K filings with Item 1.05 listed in EDGAR during the study period.

Form 8-K/A amendments are retained in the raw filing universe but excluded from the primary timing sample unless a later protocol revision states otherwise before outcome analysis.

### Within-firm control sample

Other Form 8-K filings made by firms that appear in the cyber sample during the same study period.

The broad control set is the primary comparison. A robustness specification will exclude filings containing Item 2.02 because earnings releases have a strong and predictable after-hours filing pattern.

## Primary timing outcomes

### After-hours filing

An indicator equal to one when the EDGAR acceptance time is at or after 4:00 p.m. Eastern Time.

### Friday filing

An indicator equal to one when the official filing date is Friday.

### Disclosure delay

The number of SEC business days between the stated materiality-determination date and the official filing date.

A materiality-determination date enters the confirmatory deadline analysis only after manual review of the underlying filing.

### Final-day filing

An indicator equal to one when disclosure delay equals four business days.

## Main hypotheses

### H1

Item 1.05 cybersecurity filings have a different probability of after-hours filing than other Form 8-K filings by the same issuer, after controlling for calendar time.

### H2

Item 1.05 cybersecurity filings have a different probability of Friday filing than other Form 8-K filings by the same issuer, after controlling for calendar time.

### H3

A non-trivial share of reviewed Item 1.05 filings use the full four-business-day disclosure window. The day-by-day delay distribution is reported without imposing a uniform-delay null.

### H4

Within the cyber sample, disclosure timing is associated with the subsequent market reaction. The primary return specification uses a market-model cumulative abnormal return over [0, +1], where event day zero is the first trading session in which the filing could be incorporated into prices.

## Primary timing model

For after-hours and Friday outcomes, the baseline model is a linear probability model with issuer fixed effects and calendar-month fixed effects:

outcome = beta * Item1.05 + issuer fixed effects + month fixed effects + error

Standard errors are clustered by issuer.

The coefficient on Item1.05 is interpreted as the within-issuer difference between cyber and non-cyber Form 8-K timing, conditional on calendar month.

## Event-time convention

For filings accepted before 4:00 p.m. Eastern Time on a trading day, event day zero is that trading day.

For filings accepted at or after 4:00 p.m., on a weekend, or on a market holiday, event day zero is the next NYSE trading session.

The primary market model uses an estimation window from trading day -130 through -30 and SPY as the benchmark. Primary CAR is [0, +1]. Additional windows are [-1, +1], [0, +2], and [0, +5].

## Manual review

Automated text extraction is used only to produce candidate materiality dates.

Each candidate used in the deadline analysis must be checked against the source filing. The reviewed date and inclusion decision are stored in data/manual/materiality_annotations.csv.

Manual annotations are inputs to the pipeline and are never silently written into generated datasets.

## Exclusions

A filing is excluded from the deadline analysis when:

- no materiality-determination date can be established from the filing or a clearly linked amendment;
- the filing is an amendment rather than the first Item 1.05 disclosure;
- an authorized disclosure delay makes the ordinary four-business-day rule inapplicable and the delay cannot be reconstructed cleanly; or
- the reported chronology is internally inconsistent.

A filing may remain in the after-hours and Friday analyses even if it is excluded from the deadline analysis.

Market-analysis exclusions are documented individually in data/manual/issuer_overrides.csv.

## Robustness checks

Planned robustness checks include:

- excluding Item 2.02 earnings-related control filings;
- restricting controls to a symmetric window around each firm's cyber filing;
- using 4:30 p.m. and 5:00 p.m. as alternative after-hours thresholds;
- estimating logit specifications alongside the linear probability model;
- using simple market-adjusted returns alongside the market model;
- separating ransomware and third-party incidents when sufficient observations are available;
- excluding filings with simultaneous major non-cyber corporate news.

## Exploratory analyses

Incident type, incident-discovery-to-materiality lag, operational disruption, data exfiltration, and stated financial impact are exploratory until the coding scheme is frozen.

No exploratory variable will be promoted to a confirmatory outcome after results are observed.
