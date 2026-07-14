#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv("/data/demo-surveillance/demo.csv")
summary = df.describe()
summary.to_csv("/output/summary.csv")
print(f"Analysis complete. Processed {len(df)} rows, {len(df.columns)} columns.")
