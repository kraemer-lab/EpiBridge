## Demonstration Surveillance Summary

A minimal example analysis that reads the demonstration surveillance dataset and computes summary statistics.

### Prerequisites

- [Python 3.14](/environments/python-3.14) Execution Environment
- [Demonstration Surveillance Dataset](/resources/demo-surveillance) Data Resource

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
  -v $(pwd)/../../resources/demo-surveillance/data:/data/demo-surveillance:ro \
  epibridge/python-3.14:latest \
  python /analysis/run.py
```
