# Demonstration Surveillance Dataset — Schema

Applies to:

  `data/demo.csv`

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | Unique patient identifier |
| `age` | integer | Patient age in years |
| `region` | string | Geographic region (North, South, East, West) |
| `outcome` | string | Clinical outcome (recovered, deceased) |
| `exposed` | string | Known exposure (yes, no) |
| `vaccinated` | string | Vaccination status (yes, no) |

## Constraints

- `id` is unique per record.
- `age` must be a positive integer (0–120).
- `region` must be one of the four defined regions.
- `outcome` is a binary categorical variable.
- Missing values are not present in this dataset.
