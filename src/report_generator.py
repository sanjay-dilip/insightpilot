"""Assembles a structured markdown report from a data profiler dictionary."""

import os
from datetime import datetime
from pathlib import Path


def generate_report(profile: dict, output_dir: str = "outputs/sample_reports") -> str:
    """Write a structured markdown report from a profiler dict to disk.

    Args:
        profile: Dictionary produced by data_profiler.profile_dataset.
        output_dir: Directory where the report file will be saved.

    Returns:
        The full filepath of the saved markdown report.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    source_stem = Path(profile["filepath"]).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_stem}_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)

    lines = []

    # ------------------------------------------------------------------ #
    # Section 1 — Dataset Overview
    # ------------------------------------------------------------------ #
    lines.append("# Data Profile Report\n")
    lines.append("## 1. Dataset Overview\n")
    lines.append(f"- **Source file:** `{profile['filepath']}`")
    lines.append(f"- **Row count:** {profile['row_count']:,}")
    lines.append(f"- **Column count:** {profile['column_count']}")

    dup = profile["duplicate_row_count"]
    if dup > 0:
        lines.append(
            f"- **Duplicate rows:** {dup:,} — "
            "duplicate rows detected. Review before analysis."
        )
    else:
        lines.append("- **Duplicate rows:** 0")

    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 2 — Data Quality Summary
    # ------------------------------------------------------------------ #
    lines.append("## 2. Data Quality Summary\n")
    lines.append("| Column Name | Data Type | Missing Count | Missing % |")
    lines.append("|-------------|-----------|---------------|-----------|")
    for col in profile["columns"]:
        lines.append(
            f"| {col['name']} | {col['dtype']} "
            f"| {col['missing_count']:,} | {col['missing_pct']}% |"
        )
    lines.append("")

    missing_cols = [c for c in profile["columns"] if c["missing_count"] > 0]
    if missing_cols:
        lines.append("> **Columns with missing values**")
        for col in missing_cols:
            lines.append(
                f"> - `{col['name']}`: "
                f"{col['missing_count']:,} missing ({col['missing_pct']}%)"
            )
    else:
        lines.append("No missing values detected.")

    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 3 — Column Profiles
    # ------------------------------------------------------------------ #
    lines.append("## 3. Column Profiles\n")
    for col in profile["columns"]:
        lines.append(f"### `{col['name']}`\n")
        lines.append(f"- **Type:** {col['dtype']}")
        lines.append(
            f"- **Missing:** {col['missing_count']:,} ({col['missing_pct']}%)"
        )
        lines.append("")

        if col["numeric_stats"] is not None:
            s = col["numeric_stats"]
            lines.append("| Min | Max | Mean | Median | Std Dev |")
            lines.append("|-----|-----|------|--------|---------|")
            lines.append(
                f"| {s['min']} | {s['max']} | {s['mean']} "
                f"| {s['median']} | {s['std']} |"
            )

        elif col["categorical_stats"] is not None:
            s = col["categorical_stats"]
            lines.append(f"- **Unique values:** {s['unique_count']:,}")
            lines.append("")
            lines.append("| Value | Count |")
            lines.append("|-------|-------|")
            for value, count in s["top_5"].items():
                lines.append(f"| {value} | {count:,} |")

        lines.append("")

    # ------------------------------------------------------------------ #
    # Section 4 — Limitations
    # ------------------------------------------------------------------ #
    lines.append("## 4. Limitations\n")
    lines.append(
        "This report is based solely on automated data profiling. "
        "It reflects the structure and surface statistics of the dataset. "
        "It does not draw conclusions about causation, statistical significance, "
        "or business outcomes. Any decisions based on this data should involve "
        "further domain-specific analysis."
    )
    lines.append("")

    report_text = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    return output_path


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.data_profiler import profile_dataset

    profile = profile_dataset("data/sample_datasets/census_income.csv")
    saved_path = generate_report(profile)
    print(f"Report saved to: {saved_path}")
    print("\n--- First 30 lines ---\n")
    with open(saved_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= 30:
                break
            print(line, end="")
