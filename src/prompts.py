"""
LLM prompt template functions for InsightPilot Build 2.

Each function takes structured data and returns a fully assembled prompt string
ready to send to an LLM. No API calls are made here — these are pure
string-building functions.
"""

from src.schemas import AnalysisResult


def build_business_questions_prompt(profile: dict, analysis: AnalysisResult) -> str:
    """Build a prompt asking the LLM to suggest 3-5 business questions for this dataset.

    Takes the profile dict (from data_profiler.profile_dataset) and an
    AnalysisResult (from analysis_tools.run_analysis). Returns a single prompt
    string.

    The prompt instructs the model to:
    - Only reference column names that appear in the dataset (listed explicitly).
    - Not invent statistics, trends, or facts not present in the supplied data.
    - Treat the domain as uncertain if topic confidence is "low".
    - Respond as a numbered list with no preamble.
    """
    column_names = [col["name"] for col in profile["columns"]]
    column_list = ", ".join(column_names)

    confidence_instruction = ""
    if analysis.inferred_topic_confidence == "low":
        confidence_instruction = (
            "The dataset's domain could not be confidently determined from column names. "
            "Treat the dataset's purpose as uncertain — do not assume a specific domain. "
            "Suggest general analytical questions that would apply to this data regardless of domain."
        )
    else:
        confidence_instruction = (
            f"The dataset appears to be about: {analysis.inferred_topic} "
            f"(confidence: {analysis.inferred_topic_confidence}). "
            "Use this as context when suggesting questions, but do not treat it as definitive."
        )

    prompt = f"""You are a data analyst reviewing a dataset. Your task is to suggest 3 to 5 business or analytical questions that this dataset could be used to answer.

DATASET OVERVIEW:
- Rows: {profile["row_count"]}
- Columns: {profile["column_count"]}
- Column names (you may only reference these exact names): {column_list}

DOMAIN CONTEXT:
{confidence_instruction}

STRICT RULES — you must follow these exactly:
1. You may only reference column names from the list above. Do not invent or assume the existence of any other columns.
2. Do not invent statistics, trends, or facts that are not explicitly provided in this prompt.
3. Each question must be answerable using only the columns listed above.
4. If the dataset's domain is uncertain, do not assume a specific industry or purpose.

OUTPUT FORMAT:
Respond as a numbered list. One question per line. No preamble, no explanation, no trailing commentary.

Example format:
1. <question>
2. <question>
3. <question>
"""
    return prompt


def build_summary_prompt(profile: dict, analysis: AnalysisResult) -> str:
    """Build a prompt asking the LLM to write a plain-language dataset summary.

    Takes the profile dict (from data_profiler.profile_dataset) and an
    AnalysisResult (from analysis_tools.run_analysis). Returns a single prompt
    string.

    The prompt includes row count, column count, duplicate count, and the full
    list of detected quality issues. The model is instructed to reference only
    the issues listed — not infer or assume additional ones.
    """
    if analysis.quality_issues:
        issues_text = "\n".join(
            f"  - Column '{issue.column}': {issue.issue_type} (severity: {issue.severity}) — {issue.description}"
            for issue in analysis.quality_issues
        )
    else:
        issues_text = "  No quality issues detected."

    prompt = f"""You are a data analyst writing a report introduction. Write a 2 to 3 sentence plain-language summary describing what this dataset contains and its overall data quality.

DATASET FACTS:
- Row count: {profile["row_count"]}
- Column count: {profile["column_count"]}
- Duplicate rows: {profile["duplicate_row_count"]}
- Inferred topic: {analysis.inferred_topic} (confidence: {analysis.inferred_topic_confidence})

DATA QUALITY ISSUES DETECTED:
{issues_text}

STRICT RULES — you must follow these exactly:
1. Reference only the quality issues listed above. Do not infer, assume, or mention any issues not explicitly listed.
2. Use only the facts provided in this prompt — do not invent additional statistics or observations.
3. Write in plain language suitable for a non-technical business audience.
4. Do not speculate about causes of quality issues — only describe what was detected.

OUTPUT FORMAT:
Write exactly 2 to 3 sentences. No bullet points. No headers. No preamble. Plain prose only.
"""
    return prompt


def build_findings_prompt(profile: dict, analysis: AnalysisResult) -> str:
    """Build a prompt asking the LLM to draft 3-5 grounded ReportFinding-style findings.

    Takes the profile dict (from data_profiler.profile_dataset) and an
    AnalysisResult (from analysis_tools.run_analysis). Returns a single prompt
    string.

    The prompt supplies the quality issues and correlations as raw material and
    instructs the model to produce structured findings with a finding, evidence,
    and column_references field for each. This structure matches ReportFinding
    in src.schemas and will be parsed by agent.py.

    Core guardrails enforced in the prompt:
    - Every finding must cite a specific column name and a specific computed value.
    - If the data does not support a confident claim, the model must say so rather
      than speculate.
    - Correlation must never be described as causation.
    """
    column_names = [col["name"] for col in profile["columns"]]
    column_list = ", ".join(column_names)

    if analysis.quality_issues:
        issues_text = "\n".join(
            f"  - Column '{issue.column}': {issue.issue_type} (severity: {issue.severity}) — {issue.description}"
            for issue in analysis.quality_issues
        )
    else:
        issues_text = "  None detected."

    if analysis.correlations:
        correlations_text = "\n".join(
            f"  - {c.column_a} vs {c.column_b}: r = {c.correlation_coefficient} ({c.strength_label})"
            for c in analysis.correlations
        )
    else:
        correlations_text = "  None detected."

    prompt = f"""You are a data analyst writing structured findings for a dataset report. Your task is to draft 3 to 5 findings based strictly on the computed data provided below.

DATASET OVERVIEW:
- Rows: {profile["row_count"]}
- Columns: {profile["column_count"]}
- Valid column names (you may only reference these): {column_list}

COMPUTED QUALITY ISSUES:
{issues_text}

COMPUTED CORRELATIONS (Pearson r):
{correlations_text}

STRICT RULES — you must follow these exactly:
1. Every finding must cite a specific column name from the list above and a specific computed value from the quality issues or correlations provided. A finding with no traceable number or fact is not acceptable.
2. If the available data does not clearly support a conclusion, state that explicitly rather than guessing. Do not speculate beyond what the numbers show.
3. Never describe a correlation as causation. If two columns are correlated, describe it as correlation only — never imply that one causes the other.
4. Do not reference any column not listed above. Do not invent statistics not present in this prompt.

OUTPUT FORMAT:
Output one block per finding, using exactly this structure. Do not add any text outside these blocks.

FINDING: <one sentence stating the observation>
EVIDENCE: <the specific computed value or column reference that supports this finding>
COLUMN_REFERENCES: <comma-separated list of column names this finding cites>

---

Repeat this block 3 to 5 times. Separate each block with ---. No preamble. No trailing commentary.
"""
    return prompt
