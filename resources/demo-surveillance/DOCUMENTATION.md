# Demonstration Surveillance Dataset

## Overview

A 50-record synthetic surveillance dataset for platform demonstration, analysis development and integration testing. Contains patient demographics, exposure history, vaccination status and clinical outcomes. Designed for summary statistics, stratification and basic epidemiological exploration.

All records are artificially generated. No conclusions drawn from this dataset have scientific validity.

## Runtime Access

Inside an execution container, the dataset is mounted at:

```
/data/demo-surveillance/
```

Your analysis code reads files from this path using the container's standard I/O libraries. For example, with Python and pandas:

```python
import pandas as pd
df = pd.read_csv("/data/demo-surveillance/demo.csv")
print(df.describe())
```

This path is identical for validation runs (representative data) and governed execution (production data). Your code does not need to change between environments.

### Runtime contents

The dataset currently contains:

- `demo.csv` — synthetic surveillance records (50 rows, 6 columns)
  (1.4 KB)

## Column Reference

| Column | Type | Values | Description |
|--------|------|--------|-------------|
| `id` | integer | 1–50 | Unique patient identifier |
| `age` | integer | 22–74 | Patient age in years |
| `region` | string | North, South, East, West | Geographic region |
| `outcome` | string | recovered, deceased | Clinical outcome |
| `exposed` | string | yes, no | Known exposure to pathogen |
| `vaccinated` | string | yes, no | Vaccination status |

## Intended Analyses

- Summary statistics
- Stratification by region or outcome
- Exposure–outcome contingency tables
- Age distribution analysis
- Demonstration of the standard Canada execution contract (CSV input,
  pandas transformation, CSV output)

## Caveats

- **Synthetic data**: All records are artificially generated. No conclusions drawn from this dataset have scientific validity.
- **Region labels**: Geographic region names (North, South, East, West) are placeholders and do not correspond to actual administrative boundaries.
- **Sample size**: 50 records. Real-world surveillance datasets would be orders of magnitude larger.
- **Outcome definition**: Outcome labels are illustrative only and do not reflect any real clinical classification system.

## Related Resources

- [Demonstration Surveillance Summary](/examples/demo) — example analysis that reads this dataset
- [Python 3.14](/environments/python-3.14) — execution environment used by the example analysis
