"""Orchestrates the Build 2 InsightPilot agent workflow.

Loads a CSV once, runs the deterministic analysis pipeline, calls the Gemini
API using the prompt templates in src.prompts, parses the responses into the
structured schemas in src.schemas, and assembles a single AgentReport.
"""

import logging
import os
import re

import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv

from src.analysis_tools import run_analysis
from src.data_profiler import profile_dataset
from src.prompts import (
    build_business_questions_prompt,
    build_findings_prompt,
    build_summary_prompt,
)
from src.schemas import AgentReport, BusinessQuestion, ReportFinding

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_NAME = "gemini-2.5-flash"
_NUMBERED_LINE_RE = re.compile(r"^\d+\.\s*(.+)$")


def load_data(filepath: str) -> tuple[dict, pd.DataFrame]:
    """Load a CSV exactly once and return a matched profile/DataFrame pair.

    Calls profile_dataset() to get the structured profile, then separately
    reads the same CSV into a DataFrame and applies the identical "?"
    normalization that profile_dataset applies internally (replace "?",
    with optional surrounding whitespace, with pd.NA via regex). This logic
    is copied verbatim from src/data_profiler.py rather than reimplemented,
    so the two stay in lockstep.

    This matters because analysis_tools.py trusts the profile's column list
    as ground truth and indexes into the df by column name. If the profile
    and the DataFrame came from separate, differently-normalized loads, the
    column statistics in the profile could silently disagree with the values
    analysis_tools computes from the df. Every other function in this module
    must receive its df and profile from this single load — never call
    pd.read_csv independently elsewhere in this file.

    Args:
        filepath: Path to the CSV file to load.

    Returns:
        A (profile, df) tuple: the structured profile dict from
        profile_dataset(), and the normalized DataFrame used to produce it.

    Raises:
        FileNotFoundError: If no file exists at the given filepath.
    """
    profile = profile_dataset(filepath)

    df = pd.read_csv(filepath)
    df = df.replace(r"^\s*\?\s*$", pd.NA, regex=True)

    return profile, df


def call_gemini(prompt: str, model_name: str = _DEFAULT_MODEL_NAME) -> str:
    """Send a single prompt to the Gemini API and return the response text.

    Reads GEMINI_API_KEY from the environment (via python-dotenv) before
    attempting the call. If the key is missing, raises immediately rather
    than attempting a call that is guaranteed to fail.

    Args:
        prompt: The fully assembled prompt string to send.
        model_name: The Gemini model to use.

    Returns:
        The model's response text.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set, or if the API call
            fails for any reason (network error, API error, etc.). The
            error message identifies which step failed.
    """
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "call_gemini: GEMINI_API_KEY is not set in the environment or .env file"
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as exc:
        raise RuntimeError(f"call_gemini: Gemini API call failed: {exc}") from exc


def parse_business_questions(raw_text: str) -> list[BusinessQuestion]:
    """Parse a numbered-list Gemini response into BusinessQuestion objects.

    Expects the format produced by build_business_questions_prompt: one
    question per line, prefixed with "<number>. ".

    KNOWN LIMITATION: build_business_questions_prompt's output format does
    not separately provide relevant_columns or a rationale for each
    question, so both fields are set to their empty defaults
    (relevant_columns=[], rationale="") rather than guessed at.

    Args:
        raw_text: The raw response text from call_gemini().

    Returns:
        A list of BusinessQuestion objects. Returns an empty list (with a
        logged warning) if no numbered lines are found.
    """
    questions: list[BusinessQuestion] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        match = _NUMBERED_LINE_RE.match(line)
        if not match:
            continue

        question_text = match.group(1).strip()
        if question_text:
            questions.append(
                BusinessQuestion(
                    question=question_text,
                    relevant_columns=[],
                    rationale="",
                )
            )

    if not questions:
        logger.warning(
            "parse_business_questions: no numbered question lines found in response"
        )

    return questions


def parse_findings(raw_text: str) -> list[ReportFinding]:
    """Parse FINDING/EVIDENCE/COLUMN_REFERENCES blocks into ReportFinding objects.

    Expects the format produced by build_findings_prompt: blocks separated
    by "---", each containing lines prefixed with "FINDING:", "EVIDENCE:",
    and "COLUMN_REFERENCES:".

    Args:
        raw_text: The raw response text from call_gemini().

    Returns:
        A list of ReportFinding objects. Blocks missing any of the three
        required fields are skipped (with a logged warning) rather than
        included with a missing field. Returns an empty list (with a logged
        warning) if zero valid blocks are found in a non-empty response.
    """
    findings: list[ReportFinding] = []
    blocks = raw_text.split("---")

    for block in blocks:
        finding_text = None
        evidence_text = None
        column_refs: list[str] = []
        has_column_refs_line = False

        for line in block.splitlines():
            line = line.strip()
            if line.startswith("FINDING:"):
                finding_text = line[len("FINDING:") :].strip()
            elif line.startswith("EVIDENCE:"):
                evidence_text = line[len("EVIDENCE:") :].strip()
            elif line.startswith("COLUMN_REFERENCES:"):
                has_column_refs_line = True
                raw_refs = line[len("COLUMN_REFERENCES:") :].strip()
                column_refs = [
                    ref.strip() for ref in raw_refs.split(",") if ref.strip()
                ]

        if not finding_text or not evidence_text or not has_column_refs_line:
            if block.strip():
                logger.warning(
                    "parse_findings: skipping block missing a required field: %r",
                    block.strip()[:80],
                )
            continue

        findings.append(
            ReportFinding(
                finding=finding_text,
                evidence=evidence_text,
                column_references=column_refs,
            )
        )

    if not findings and raw_text.strip():
        logger.warning("parse_findings: no valid FINDING blocks parsed from response")

    return findings


def run_agent(filepath: str) -> AgentReport:
    """Run the full InsightPilot agent workflow for one CSV file.

    Steps:
        1. Load the profile and DataFrame once via load_data().
        2. Run the deterministic analysis pipeline via analysis_tools.run_analysis().
        3. Call Gemini for business questions and parse the response.
        4. Call Gemini for a plain-language summary (stored raw, not parsed
           into a schema object — report_generator.py consumes it as text).
        5. Call Gemini for findings and parse the response.
        6. Guardrail check: drop any parsed finding that references a column
           not present in the profile, logging the hallucinated column name.
        7. Assemble and return an AgentReport.

    FALLBACK BEHAVIOR: each Gemini call is wrapped in its own try/except. If
    a call fails, the failure is logged and that step's output is treated as
    empty (no business questions, an empty summary, or no findings) rather
    than aborting the whole run — a partial report with a logged gap is
    preferred over no report at all. This function does not implement retry
    logic, caching, or rate-limit handling.

    The summary text produced in step 4 is currently not attached to
    AgentReport, since AgentReport has no summary field — it is logged for
    now. limitations is left as an empty list at this stage:
    report_generator.py already has its own static limitations section, so
    this field is not yet populated here.

    Args:
        filepath: Path to the CSV file to analyze.

    Returns:
        An AgentReport with the analysis results, parsed business questions,
        and guardrail-checked findings.
    """
    profile, df = load_data(filepath)
    analysis = run_analysis(profile, df)

    valid_column_names = {col["name"] for col in profile["columns"]}

    business_questions: list[BusinessQuestion] = []
    try:
        questions_prompt = build_business_questions_prompt(profile, analysis)
        questions_raw = call_gemini(questions_prompt)
        business_questions = parse_business_questions(questions_raw)
    except RuntimeError as exc:
        logger.warning("run_agent: business questions step failed: %s", exc)

    try:
        summary_prompt = build_summary_prompt(profile, analysis)
        summary_raw = call_gemini(summary_prompt)
        logger.info("run_agent: summary generated: %s", summary_raw)
    except RuntimeError as exc:
        logger.warning("run_agent: summary step failed: %s", exc)

    findings: list[ReportFinding] = []
    try:
        findings_prompt = build_findings_prompt(profile, analysis)
        findings_raw = call_gemini(findings_prompt)
        findings = parse_findings(findings_raw)
    except RuntimeError as exc:
        logger.warning("run_agent: findings step failed: %s", exc)

    guarded_findings: list[ReportFinding] = []
    for finding in findings:
        hallucinated = [
            ref for ref in finding.column_references if ref not in valid_column_names
        ]
        if hallucinated:
            logger.warning(
                "run_agent: dropping finding referencing unknown column(s) %s: %r",
                hallucinated,
                finding.finding,
            )
            continue
        guarded_findings.append(finding)

    return AgentReport(
        source_filepath=filepath,
        analysis=analysis,
        business_questions=business_questions,
        findings=guarded_findings,
        limitations=[],
    )
