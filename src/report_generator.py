"""Assembles a structured markdown report from a data profiler dictionary."""

import os
from datetime import datetime
from pathlib import Path

from src.schemas import AgentReport


def _build_dataset_overview_lines(profile: dict) -> list[str]:
    """Build the Dataset Overview section lines shared by both report types.

    Args:
        profile: Dictionary produced by data_profiler.profile_dataset.

    Returns:
        A list of markdown lines, including the section header and a
        trailing blank line.
    """
    lines = []
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
    return lines


_LIMITATIONS_STATIC_TEXT = (
    "This report is based solely on automated data profiling. "
    "It reflects the structure and surface statistics of the dataset. "
    "It does not draw conclusions about causation, statistical significance, "
    "or business outcomes. Any decisions based on this data should involve "
    "further domain-specific analysis."
)


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
    lines.extend(_build_dataset_overview_lines(profile))

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
    lines.append(_LIMITATIONS_STATIC_TEXT)
    lines.append("")

    report_text = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    return output_path


def generate_agent_report(
    report: AgentReport, profile: dict, output_dir: str = "outputs/sample_reports"
) -> str:
    """Write the full Build 2 agent markdown report to disk.

    Args:
        report: AgentReport produced by src.agent.run_agent.
        profile: Dictionary produced by data_profiler.profile_dataset for the
            same source file as report — used for the Dataset Overview
            section.
        output_dir: Directory where the report file will be saved.

    Returns:
        The full filepath of the saved markdown report.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    source_stem = Path(profile["filepath"]).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_stem}_agent_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)

    lines = []

    # ------------------------------------------------------------------ #
    # Section 1 — Dataset Overview
    # ------------------------------------------------------------------ #
    lines.append("# Agent Insight Report\n")
    lines.extend(_build_dataset_overview_lines(profile))

    # ------------------------------------------------------------------ #
    # Section 2 — Inferred Topic
    # ------------------------------------------------------------------ #
    lines.append("## 2. Inferred Topic\n")
    lines.append(f"- **Topic:** {report.analysis.inferred_topic}")
    lines.append(f"- **Confidence:** {report.analysis.inferred_topic_confidence}")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 3 — Data Quality Issues
    # ------------------------------------------------------------------ #
    lines.append("## 3. Data Quality Issues\n")
    if report.analysis.quality_issues:
        for issue in report.analysis.quality_issues:
            lines.append(
                f"- `{issue.column}` — {issue.issue_type} "
                f"(severity: {issue.severity}): {issue.description}"
            )
    else:
        lines.append("No data quality issues detected.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 4 — Correlations
    # ------------------------------------------------------------------ #
    lines.append("## 4. Correlations\n")
    if report.analysis.correlations:
        for corr in report.analysis.correlations:
            lines.append(
                f"- `{corr.column_a}` vs `{corr.column_b}`: "
                f"r = {round(corr.correlation_coefficient, 4)} ({corr.strength_label})"
            )
    else:
        lines.append("No notable correlations detected.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 5 — Suggested Business Questions
    # ------------------------------------------------------------------ #
    lines.append("## 5. Suggested Business Questions\n")
    if report.business_questions:
        for i, question in enumerate(report.business_questions, start=1):
            lines.append(f"{i}. {question.question}")
    else:
        lines.append("Business questions could not be generated for this run.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 6 — Key Findings
    # ------------------------------------------------------------------ #
    lines.append("## 6. Key Findings\n")
    if report.findings:
        for finding in report.findings:
            lines.append(f"- {finding.finding}")
            lines.append(f"  - Evidence: {finding.evidence}")
            lines.append(
                f"  - Columns referenced: {', '.join(finding.column_references)}"
            )
    else:
        lines.append("Findings could not be generated for this run.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 7 — Limitations
    # ------------------------------------------------------------------ #
    lines.append("## 7. Limitations\n")
    lines.append(_LIMITATIONS_STATIC_TEXT)
    if report.limitations:
        lines.append("")
        for limitation in report.limitations:
            lines.append(f"- {limitation}")
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
