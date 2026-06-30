"""Inspects a CSV dataset and returns a structured profiling dictionary."""

import re
from pprint import pprint

import pandas as pd


def profile_dataset(filepath: str) -> dict:
    """Load a CSV and return a structured profile dictionary.

    Args:
        filepath: Path to the CSV file to profile.

    Returns:
        A dictionary containing shape info, duplicate count, and per-column
        statistics including missing value counts and numeric or categorical stats.

    Raises:
        FileNotFoundError: If no file exists at the given filepath.
    """
    import os

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No file found at: {filepath}")

    df = pd.read_csv(filepath)

    # Normalize "?" (with optional surrounding whitespace) to NaN in every column
    df = df.replace(r"^\s*\?\s*$", pd.NA, regex=True)

    row_count: int = len(df)
    column_count: int = len(df.columns)
    duplicate_row_count: int = int(df.duplicated().sum())

    columns = []
    for col in df.columns:
        series = df[col]
        missing_count = int(series.isna().sum())
        missing_pct = round(missing_count / row_count * 100, 2) if row_count else 0.0

        numeric_stats = None
        categorical_stats = None

        if pd.api.types.is_numeric_dtype(series):
            numeric_stats = {
                "min": round(float(series.min()), 2),
                "max": round(float(series.max()), 2),
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
                "std": round(float(series.std()), 2),
            }
        else:
            top5 = series.value_counts().head(5)
            categorical_stats = {
                "unique_count": int(series.nunique()),
                "top_5": {str(k): int(v) for k, v in top5.items()},
            }

        columns.append(
            {
                "name": col,
                "dtype": str(series.dtype),
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "numeric_stats": numeric_stats,
                "categorical_stats": categorical_stats,
            }
        )

    return {
        "filepath": filepath,
        "row_count": row_count,
        "column_count": column_count,
        "duplicate_row_count": duplicate_row_count,
        "columns": columns,
    }


if __name__ == "__main__":
    result = profile_dataset("data/sample_datasets/census_income.csv")
    pprint(result)
