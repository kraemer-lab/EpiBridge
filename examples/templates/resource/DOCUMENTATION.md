# {{NAME}}

## Overview

TODO: Describe the dataset — provenance, scope, intended analyses, and relevant caveats.

## Runtime Access

Inside an execution container, the dataset is mounted at:

```
/data/{{ALIAS}}/
```

Your analysis code reads files from this path using the container's standard I/O libraries. This path is identical for validation runs (representative data) and governed execution (production data).

### Runtime contents

- TODO: List the files available at the mount path

## Column Reference

| Column | Type | Values | Description |
|--------|------|--------|-------------|
| TODO   |      |        |             |
| TODO   |      |        |             |
| TODO   |      |        |             |

## Intended Analyses

- TODO: List appropriate use cases
- TODO: Describe what this dataset supports

## Caveats

- TODO: Document limitations and restrictions
