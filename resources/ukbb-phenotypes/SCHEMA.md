# UK Biobank Phenotypes — Schema

## Database

The phenotype data is stored in a DuckDB database (`phenotypes.duckdb`).

## Tables

### `participants`

| Column | Type | Description |
|--------|------|-------------|
| `eid` | integer | Unique participant identifier |
| `sex` | string | Biological sex (male, female) |
| `year_of_birth` | integer | Year of birth |
| `ethnicity` | string | Self-reported ethnic group |

### `assessments`

| Column | Type | Description |
|--------|------|-------------|
| `eid` | integer | Participant identifier (foreign key) |
| `assessment_date` | date | Date of assessment centre visit |
| `bmi` | float | Body mass index (kg/m²) |
| `systolic_bp` | integer | Systolic blood pressure (mmHg) |
| `diastolic_bp` | integer | Diastolic blood pressure (mmHg) |

### `outcomes`

| Column | Type | Description |
|--------|------|-------------|
| `eid` | integer | Participant identifier (foreign key) |
| `icd10_code` | string | Primary diagnosis ICD-10 code |
| `onset_date` | date | Date of first diagnosis |

## Relationships

- `participants.eid → assessments.eid` (one-to-many)
- `participants.eid → outcomes.eid` (one-to-many)
