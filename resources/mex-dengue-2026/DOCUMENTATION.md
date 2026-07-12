# Mexico Dengue Surveillance 2026 — Documentation

## Overview

This dataset contains dengue surveillance records from Mexico during the 2026 calendar year. It is intended for epidemiological analysis of dengue transmission, vaccine effectiveness, and outcome prediction.

## Data Collection

Records are collected through the national surveillance system operated by the Mexican Ministry of Health. Each record represents a confirmed dengue case with demographic and clinical information.

## Known Caveats

- **Geographic coverage**: Data are available for four primary regions only. Sub-regional analysis is not supported.
- **Outcome definition**: "Deceased" includes both directly attributable and contributing cause dengue deaths per WHO definitions.
- **Exposure history**: Self-reported; may be subject to recall bias.
- **Vaccination status**: Includes individuals who received at least one dose of a WHO-approved dengue vaccine.

## Usage Notes

- The dataset is intended for population-level analysis, not clinical decision-making.
- When performing stratified analysis by region, note that population denominators vary significantly.
- The representative dataset (`representative.csv`) contains a 50-record sample suitable for local development and bundle testing.

## Related Resources

- World Health Organization — Dengue and severe dengue (https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue)
- Mexican Ministry of Health — Epidemiological Bulletin
