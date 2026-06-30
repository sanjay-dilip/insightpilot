"""
Pure Pandas analysis functions for InsightPilot Build 2.

No LLM calls, no network access. All functions are deterministic.
Entry point for agent.py is run_analysis().
"""

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.schemas import AnalysisResult, CorrelationFinding, DataQualityIssue

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Topic keyword map: topic label -> list of trigger substrings (case-insensitive).
# A column name matching any substring in a list counts as one trigger hit for
# that topic. Confidence is determined by how many distinct triggers match.
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "income/demographics": [
        "age",
        "income",
        "education",
        "occupation",
        "workclass",
        "marital",
        "race",
        "sex",
        "hours",
        "native",
        "relationship",
        "capital",
    ],
    "sales/transactions": [
        "sale",
        "revenue",
        "order",
        "product",
        "quantity",
        "price",
        "discount",
        "transaction",
        "purchase",
        "amount",
        "invoice",
        "item",
    ],
    "customer/crm": [
        "customer",
        "client",
        "churn",
        "segment",
        "loyalty",
        "satisfaction",
        "nps",
        "contact",
        "account",
        "subscription",
        "tenure",
        "region",
    ],
    "employee/hr": [
        "employee",
        "salary",
        "department",
        "hire",
        "tenure",
        "performance",
        "attrition",
        "role",
        "manager",
        "headcount",
        "leave",
        "promotion",
    ],
    "financial": [
        "balance",
        "credit",
        "debt",
        "loan",
        "interest",
        "tax",
        "profit",
        "loss",
        "asset",
        "liability",
        "equity",
        "cash",
    ],
}

_CONFIDENCE_HIGH_THRESHOLD = 3


def infer_topic(profile: dict) -> tuple[str, str]:
    """Infer the dataset's subject domain from column names using keyword matching.

    Input: the profile dict returned by data_profiler.profile_dataset().

    Scans each column name for case-insensitive substring matches against
    _TOPIC_KEYWORDS. Each distinct trigger keyword that matches at least one
    column name counts as one hit for that topic category. The topic with the
    most hits wins.

    Confidence levels:
        "high"   — winning topic has 3+ distinct keyword hits
        "medium" — winning topic has 1-2 keyword hits
        "low"    — no topic gets any match; inferred_topic is set to the
                   sentinel string "unclear — insufficient column-name signal"

    KNOWN LIMITATION: this is a heuristic over column names only, not column
    content. It will misfire on datasets with generic column names (e.g. col1,
    col2) or non-English column names. Treat the result as a hint, not a fact.

    Returns:
        (inferred_topic, confidence) — both are strings.
    """
    column_names = [col["name"].lower() for col in profile["columns"]]

    topic_scores: dict[str, int] = {}
    for topic, keywords in _TOPIC_KEYWORDS.items():
        hits = sum(
            1
            for kw in keywords
            if any(kw in col_name for col_name in column_names)
        )
        topic_scores[topic] = hits

    best_topic = max(topic_scores, key=lambda t: topic_scores[t])
    best_score = topic_scores[best_topic]

    if best_score == 0:
        logger.info("infer_topic: no keyword matches found — returning low confidence")
        return "unclear — insufficient column-name signal", "low"

    confidence = "high" if best_score >= _CONFIDENCE_HIGH_THRESHOLD else "medium"
    logger.info(
        "infer_topic: topic=%s, score=%d, confidence=%s",
        best_topic,
        best_score,
        confidence,
    )
    return best_topic, confidence


def detect_quality_issues(
    profile: dict, df: pd.DataFrame
) -> list[DataQualityIssue]:
    """Detect data quality problems in numeric columns using the profile and raw DataFrame.

    Input:
        profile — the dict returned by data_profiler.profile_dataset().
        df      — the raw pandas DataFrame loaded from the same CSV. The
                  DataFrame must not have had the "?" normalisation applied
                  (that is handled inside profile_dataset); pass the frame
                  loaded directly with pd.read_csv(). In practice agent.py
                  should pass the same frame it loaded for correlation work.

    Detects two issue types:

    outlier (severity "high" or "medium"):
        IQR method: bounds = [Q1 - 1.5*IQR, Q3 + 1.5*IQR]. Counts values
        strictly outside these bounds on non-null values. If outlier_count > 0,
        an issue is raised. Severity is "high" if outliers exceed 5% of
        non-null rows, else "medium".

    low_cardinality_numeric (severity "low"):
        Any numeric column with <= 10 distinct non-null values. This often
        means the column encodes a categorical variable as an integer. Not an
        error — surfaced as an informational flag.

    Returns:
        A list of DataQualityIssue objects. Only columns with detected issues
        are included; columns with no issues produce no entry.
    """
    issues: list[DataQualityIssue] = []

    numeric_cols = [
        col["name"]
        for col in profile["columns"]
        if col["numeric_stats"] is not None
    ]

    for col_name in numeric_cols:
        series = df[col_name].dropna()

        if series.empty:
            continue

        # --- outlier detection (IQR) ---
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())

        if outlier_count > 0:
            outlier_pct = outlier_count / len(series)
            severity = "high" if outlier_pct > 0.05 else "medium"
            description = (
                f"{outlier_count} values fall outside the IQR bounds "
                f"[{round(lower, 2)}, {round(upper, 2)}]"
            )
            issues.append(
                DataQualityIssue(
                    column=col_name,
                    issue_type="outlier",
                    description=description,
                    severity=severity,
                )
            )
            logger.debug(
                "detect_quality_issues: outlier in %s — %d values, severity=%s",
                col_name,
                outlier_count,
                severity,
            )

        # --- low cardinality numeric ---
        unique_count = int(series.nunique())
        if unique_count <= 10:
            description = (
                f"{unique_count} distinct value(s) — may be a categorical "
                f"variable encoded as numeric"
            )
            issues.append(
                DataQualityIssue(
                    column=col_name,
                    issue_type="low_cardinality_numeric",
                    description=description,
                    severity="low",
                )
            )
            logger.debug(
                "detect_quality_issues: low cardinality in %s — %d unique values",
                col_name,
                unique_count,
            )

    logger.info("detect_quality_issues: %d issues found", len(issues))
    return issues


def compute_correlations(df: pd.DataFrame) -> list[CorrelationFinding]:
    """Compute pairwise Pearson correlations for all numeric column pairs.

    Input: the raw pandas DataFrame (pd.read_csv output).

    Uses pandas .corr() (Pearson method). Self-correlations are excluded.
    Duplicate pairs are excluded — if A-B is included, B-A is not.
    Pairs where the coefficient is NaN (e.g. constant columns) are excluded.

    Strength label thresholds (applied to |r|):
        |r| < 0.3  -> "weak"
        |r| < 0.7  -> "moderate"
        |r| >= 0.7 -> "strong"

    Returns:
        A list of CorrelationFinding objects, one per valid unique pair.
    """
    numeric_df = df.select_dtypes(include="number")
    corr_matrix = numeric_df.corr(method="pearson")
    columns = list(corr_matrix.columns)

    findings: list[CorrelationFinding] = []
    seen: set[frozenset[str]] = set()

    for i, col_a in enumerate(columns):
        for col_b in columns[i + 1 :]:
            pair = frozenset({col_a, col_b})
            if pair in seen:
                continue
            seen.add(pair)

            coef = corr_matrix.loc[col_a, col_b]
            if pd.isna(coef):
                continue

            abs_coef = abs(coef)
            if abs_coef < 0.3:
                strength = "weak"
            elif abs_coef < 0.7:
                strength = "moderate"
            else:
                strength = "strong"

            findings.append(
                CorrelationFinding(
                    column_a=col_a,
                    column_b=col_b,
                    correlation_coefficient=round(coef, 4),
                    strength_label=strength,
                )
            )

    logger.info("compute_correlations: %d pairs found", len(findings))
    return findings


def run_analysis(profile: dict, df: pd.DataFrame) -> AnalysisResult:
    """Orchestrate all analysis steps and return a single AnalysisResult.

    This is the sole entry point that agent.py calls for analysis work.

    Input:
        profile — the dict returned by data_profiler.profile_dataset().
        df      — the raw pandas DataFrame loaded from the same CSV file.

    Calls:
        infer_topic(profile)
        detect_quality_issues(profile, df)
        compute_correlations(df)

    Returns:
        An AnalysisResult dataclass instance (from src.schemas).
    """
    logger.info("run_analysis: starting analysis for %s", profile.get("filepath"))

    inferred_topic, confidence = infer_topic(profile)
    quality_issues = detect_quality_issues(profile, df)
    correlations = compute_correlations(df)

    logger.info("run_analysis: complete")
    return AnalysisResult(
        inferred_topic=inferred_topic,
        inferred_topic_confidence=confidence,
        quality_issues=quality_issues,
        correlations=correlations,
    )
