# ICU Admissions 2024 — Schema

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `admission_id` | integer | Unique admission identifier |
| `patient_id` | integer | Patient identifier |
| `age` | integer | Patient age in years |
| `sex` | string | Patient sex (male, female) |
| `admission_date` | date | Date of ICU admission |
| `diagnosis` | string | Primary diagnosis at admission |
| `severity_score` | integer | APACHE II severity score (0–71) |
| `length_of_stay` | integer | ICU length of stay in days |
| `outcome` | string | Discharge outcome (survived, deceased) |

## Constraints

- `admission_id` is unique per record.
- `severity_score` ranges from 0–71 per APACHE II definition.
- `length_of_stay` is in whole days (minimum 1).
