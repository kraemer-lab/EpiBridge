## Installed Packages

This environment uses Conda (Micromamba 2.8.1) for package management. Packages are defined by the researcher rather than pre-installed.

### Base system

| Component | Version |
|-----------|---------|
| Micromamba | 2.8.1 |

### Defining dependencies

Create an `environment.yml` at the top level of your Analysis Bundle:

```yaml
name: analysis
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy
  - pandas
  - pip
```

The execution environment builder processes this file at build time.
