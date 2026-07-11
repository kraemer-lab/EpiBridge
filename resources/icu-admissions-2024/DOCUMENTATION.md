# ICU Admissions 2024 — Documentation

## Overview

This dataset contains intensive care unit admission records for calendar year 2024. It is intended for analysis of ICU resource utilisation, severity-adjusted outcomes, and admission trends.

## Data Collection

Records are extracted from the hospital information system covering all adult ICUs across participating institutions. Each record represents a single ICU episode.

## Known Caveats

- **Severity scoring**: APACHE II scores are calculated at 24 hours post-admission per standard protocol.
- **Transfers**: Inter-ICU transfers within the same institution are recorded as a single episode.
- **Readmissions**: Patients readmitted within 72 hours are recorded as a new episode but flagged in the source system.

## Usage Notes

- Length of stay analysis should account for right-censoring of patients still in ICU at data extraction.
- Severity-adjusted outcome models should include `severity_score` as a covariate.
- The representative dataset is a 100-record sample suitable for local development.

## Related Resources

- Knaus WA et al. APACHE II: A severity of disease classification system. *Crit Care Med* 1985;13(10):818-829.
