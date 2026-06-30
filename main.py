"""InsightPilot — AI Data Analyst Agent"""

import argparse
import sys

from src.data_profiler import profile_dataset
from src.report_generator import generate_agent_report, generate_report


def main() -> None:
    """Parse arguments, run profiler and report generator, exit cleanly."""
    parser = argparse.ArgumentParser(description="InsightPilot — AI Data Analyst Agent")
    parser.add_argument("csv_path", help="Path to the CSV file to analyze")
    parser.add_argument(
        "--agent",
        action="store_true",
        default=False,
        help="Run the full Build 2 agent workflow instead of the Build 1 profiler-only report.",
    )
    args = parser.parse_args()

    csv_path = args.csv_path

    if not __import__("os").path.exists(csv_path):
        print(f"Error: File not found — {csv_path}")
        sys.exit(1)

    if not csv_path.lower().endswith(".csv"):
        print(f"Error: Expected a .csv file — {csv_path}")
        sys.exit(1)

    if args.agent:
        from src.agent import run_agent

        print(f"[1/2] Running agent workflow: {csv_path}")
        agent_report = run_agent(csv_path)
        print(
            f"Done. {len(agent_report.business_questions)} business questions, "
            f"{len(agent_report.findings)} findings generated."
        )

        print("[2/2] Generating agent report...")
        profile = profile_dataset(csv_path)
        output_filepath = generate_agent_report(agent_report, profile)
        print(f"Report saved to: {output_filepath}")

        print("InsightPilot agent analysis complete.")
        sys.exit(0)

    print(f"[1/2] Profiling dataset: {csv_path}")
    profile = profile_dataset(csv_path)
    print(
        f"Done. {profile['row_count']:,} rows, {profile['column_count']} columns, "
        f"{profile['duplicate_row_count']} duplicate rows detected."
    )

    print("[2/2] Generating report...")
    output_filepath = generate_report(profile)
    print(f"Report saved to: {output_filepath}")

    print("InsightPilot analysis complete.")
    sys.exit(0)


main()
