## Mexico Dengue Summary

A minimal example analysis that reads dengue surveillance data and computes summary statistics.

### Prerequisites

- [Python 3.14](/environments/python-3.14) Execution Environment
- [Mexico Dengue Surveillance 2026](/resources/mex-dengue-2026) Data Resource

### Expected Output

- `summary.csv` — descriptive statistics for all numeric columns

### What to Learn

- How an Analysis Bundle reads a data resource from `/data`
- How an Analysis Bundle writes output to `/output`
- The standard Canada execution contract

### Local Development

```sh
docker pull epibridge/python-3.14:latest
docker run --rm -it \
  -v $(pwd):/analysis \
  -v $(pwd)/../../resources/mex-dengue-2026:/data/mexico_dengue_2026:ro \
  epibridge/python-3.14:latest \
  python /analysis/run.py
```
