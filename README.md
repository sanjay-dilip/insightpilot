# InsightPilot: An AI Data Analyst Agent

Turn raw CSV files into structured business insight reports.

## Problem
Business users and students often have CSV datasets but lack the time or skills to extract meaningful insights from them quickly.

## Solution
InsightPilot is an AI-powered data analyst agent that accepts a CSV file, inspects the data, identifies quality issues, suggests business questions, runs grounded analysis using Python and Pandas, and produces a structured insight report.

## Target User
Students, analysts, or business users who have a CSV dataset and need to understand what it contains, what problems exist in the data, what questions can be answered, and what insights can be reported.

## Agent Workflow
1. Load and inspect the CSV
2. Profile the data (columns, types, missing values, duplicates, statistics)
3. Infer what the dataset is about
4. Identify data quality issues and limitations
5. Suggest relevant business or analytical questions
6. Run grounded analysis using Pandas
7. Produce a structured insight report
8. Flag unsupported claims and limitations clearly

## Architecture
See ARCHITECTURE.md

## Tech Stack
- Python 3.10+
- Pandas
- Streamlit
- Gemini API (for summarization and report writing only)
- python-dotenv

## Setup

### 1. Clone the repo
```bash
git clone 
cd insightpilot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your API key
```

### 4. Run the terminal agent
```bash
python main.py --csv data/sample_datasets/your_file.csv
```

### 5. Run the Streamlit app
```bash
streamlit run app.py
```

## Running the Agent

InsightPilot accepts any CSV file and produces a structured markdown report.

### Requirements
Install dependencies before running:
```
pip install -r requirements.txt
```

### Basic usage
```
python main.py path/to/your/file.csv
```

### Example
```
python main.py data/sample_datasets/census_income.csv
```

### Output
The report is saved to `outputs/sample_reports/` with a timestamped filename.
Example: `census_income_20260629_192009.md`

### What the agent produces
- Dataset overview: row count, column count, duplicate row count
- Data quality summary: missing values per column with percentages
- Column profiles: statistics for every column in the dataset
- Limitations: a plain-English statement of what this report does and does not claim

## Sample Input / Output
_To be added after Build 1_

## Evaluation
_To be added after Build 4_

## Limitations
_To be added after Build 4_

## Future Improvements
_To be added after Build 5_

## Video Demo
_Link to be added_

## Kaggle Writeup
_Link to be added_
