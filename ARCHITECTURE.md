# InsightPilot — Architecture

## Overview
InsightPilot follows a multi-step agentic workflow. The LLM is used only for interpretation and report writing. All numeric analysis is performed by Python and Pandas tools.

## Agent Workflow

```
CSV Input
│
▼
[Tool: data_profiler]
  - Load CSV
  - Inspect columns, types, row count
  - Detect missing values and duplicates
  - Compute basic statistics
│
▼
[Tool: analysis_tools]
  - Infer dataset topic
  - Identify data quality issues
  - Run basic analysis (correlations, distributions, top values)
│
▼
[LLM: Gemini API]
  - Suggest business questions based on profiling output
  - Summarize findings in plain language
  - Write structured insight report
  - Flag unsupported claims
│
▼
[Tool: report_generator]
  - Assemble structured markdown report
  - Include evidence from Pandas output
  - Include limitations section
│
▼
Report Output (terminal, file, or Streamlit UI)
```

## File Responsibilities

| File | Responsibility |
|------|---------------|
| main.py | Terminal entry point |
| app.py | Streamlit UI entry point |
| src/agent.py | Orchestrates the multi-step workflow |
| src/data_profiler.py | Loads CSV and computes data profile |
| src/analysis_tools.py | Runs Pandas-based analysis |
| src/prompts.py | Stores all LLM prompt templates |
| src/schemas.py | Defines structured output schemas |
| src/evaluator.py | Runs evaluation against test cases |
| src/report_generator.py | Assembles the final markdown report |
| src/utils.py | Shared utility functions |

## Key Design Decisions
- LLM handles language, Pandas handles numbers
- All LLM inputs include actual data statistics, not assumptions
- The agent always runs the full profiling step before any analysis
- Guardrails check that findings reference actual column names and computed values
- The report always includes a limitations section

## Tech Stack
- Python 3.10+
- Pandas for all data analysis
- Gemini API for language tasks
- Streamlit for the demo UI
- python-dotenv for environment variable management
