"""
Structured output schemas for InsightPilot Build 2.

All dataclasses in this module are pure data containers — no validation logic,
no methods beyond what the dataclass decorator provides. Validation and
construction logic live in analysis_tools.py and agent.py.
"""

from dataclasses import dataclass


@dataclass
class DataQualityIssue:
    """
    A single data quality problem detected in a column.

    Expected values for issue_type (not enforced):
        "outlier"                 — a value or stat falls far outside the
                                    expected range for the column
        "low_cardinality_numeric" — a numeric column has very few distinct
                                    values, suggesting it may be categorical
        "suspicious_range"        — min/max values are implausible for the
                                    column's apparent domain

    Expected values for severity (not enforced):
        "low"    — informational; unlikely to affect analysis
        "medium" — may skew aggregates or model outputs
        "high"   — likely to produce incorrect results if not addressed

    The description field must be grounded in actual computed values (e.g.
    "missing_pct is 5.64%"), not a vague assertion.
    """

    column: str
    issue_type: str
    description: str
    severity: str


@dataclass
class CorrelationFinding:
    """
    A pairwise Pearson correlation between two numeric columns.

    The strength_label is assigned by analysis_tools.py using these thresholds
    (documented here for reference — logic does not live in this file):
        |r| < 0.3   -> "weak"
        |r| < 0.7   -> "moderate"
        |r| >= 0.7  -> "strong"

    correlation_coefficient is the raw Pearson r value in [-1.0, 1.0].
    """

    column_a: str
    column_b: str
    correlation_coefficient: float
    strength_label: str


@dataclass
class AnalysisResult:
    """
    Aggregated output of the analysis_tools pipeline for one dataset.

    inferred_topic_confidence reflects how clearly the column names and
    distributions point to a single domain. Expected values: "low", "medium",
    "high" (not enforced).
    """

    inferred_topic: str
    inferred_topic_confidence: str
    quality_issues: list[DataQualityIssue]
    correlations: list[CorrelationFinding]


@dataclass
class BusinessQuestion:
    """
    A data-grounded question the dataset can support answering.

    The rationale field must explain which columns or statistics make this
    question tractable — it is not a restatement of the question itself.
    """

    question: str
    relevant_columns: list[str]
    rationale: str


@dataclass
class ReportFinding:
    """
    A single claim made in the final report, with its grounding evidence.

    The evidence field is the primary guardrail mechanism: it must contain the
    specific computed value or column reference that supports the claim (e.g.
    "mean age = 38.58, std = 13.64"). A finding with an empty evidence field
    is invalid and will be rejected during guardrail validation in a later
    build. column_references lists every column name cited so that the
    guardrail pass can cross-check them against the actual data profile.
    """

    finding: str
    evidence: str
    column_references: list[str]


@dataclass
class AgentReport:
    """
    The complete structured output produced by the InsightPilot agent for
    one CSV file. This is the top-level object handed to report_generator.py.
    """

    source_filepath: str
    analysis: AnalysisResult
    business_questions: list[BusinessQuestion]
    findings: list[ReportFinding]
    limitations: list[str]
