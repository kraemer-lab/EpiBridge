# UK Biobank Phenotypes — Documentation

## Overview

The UK Biobank Phenotypes dataset provides a curated subset of the UK Biobank cohort study, focusing on commonly used phenotypes for epidemiological research.

## Data Source

UK Biobank is a large-scale biomedical database containing genetic, phenotypic, and health-related data from approximately 500,000 participants aged 40–69 at recruitment.

## Available Data

This published subset contains three tables:

- **participants**: Demographic data
- **assessments**: Physical measurements from assessment centre visits
- **outcomes**: ICD-10 coded health outcomes

## Usage Notes

- The DuckDB database supports SQL queries directly against the `.duckdb` file.
- Use parameterised queries to select the specific phenotypes required for your analysis.
- The representative dataset is a small extract; full data access requires institutional approval.

## Ethical Use

Researchers must comply with UK Biobank access policies and data usage agreements. No individual-level data should be disclosed in published outputs.
