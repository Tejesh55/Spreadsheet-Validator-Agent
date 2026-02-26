# Spreadsheet Validator Agent

This project implements a multi-agent workflow that ingests an Excel or CSV file, performs deterministic table validations, enables human-in-the-loop (HITL) row-by-row fixes, and generates formatted output files.

Built with **Python**, **Streamlit**, **LangGraph**, and **LangChain**.

## 🚀 Features & Capabilities

- **File Ingestion:** Accepts `.csv` or `.xlsx` files, automatically detects headers, and normalizes column data types.
- **Deterministic Validation:** Applies strict, rule-based validation per row (e.g., regex checks, value bounds, date bounds, cross-field requirements).
- **Human-in-the-Loop (HITL) Fixes:** Instead of outright rejecting an entire spreadsheet, an interactive chat agent asks the user to provide corrections for specific missing or invalid fields.
- **Intelligent Reprocessing:** Employs a canonical row hashing mechanism to selectively revalidate only the rows that were updated by the user, skipping already-fixed ones.
- **Data Transformation:** Dynamically computes new columns (`amount_usd`, `cost_center`, `approval_required`) based on user-provided global variables.
- **Output Generation:** Emits two comprehensive Excel files:
  - `success.xlsx`: All valid and successfully corrected rows.
  - `errors.xlsx`: Remaining invalid rows alongside explicit, machine-readable `error_reason`s.

## 🛠️ Workflow Architecture

The AI orchestrator processes the graph roughly as follows:
1. **Ingestor**: Reads the uploaded file, sanitizes missing data, and drops trailing computed columns.
2. **Validator**: Iterates over data using strict rules. Branches output into a temporary successful dataset and an errored dataset.
3. **Fix-Loop (HITL)**: For errored rows, the Agent prompts the user via the chat UI. It maps conversational replies to structured data updates.
4. **Packager**: Generates downloadable memory buffers (`success.xlsx` and `errors.xlsx`) containing the final output.

## 💻 How to Run Locally

### 1. Prerequisites
Ensure you have Python 3.9+ installed.

```bash
# Clone the repository and navigate to the directory
cd stanford_assignment

# (Optional but recommended) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies
Install the required packages using `pip`. (Assumes `uv` or `pip` is available).

```bash
pip install -r requirements.txt
```

### 3. API Key Configuration
The application leverages an LLM (Groq API) for generating conversational prompts. The API key is currently configured directly in `src/agent/agent.py`. Make sure your key has access, or you may configure it there.

### 4. Start the Application
Run the Streamlit application:

```bash
streamlit run app.py
```

This will launch a local web server (typically at `http://localhost:8501`).

## 🎮 Usage Guide

1. **Upload File:** Use the `➕ Upload file` button in the UI to attach a `.csv` or `.xlsx` dataset (e.g., `sample_data/expenses.xlsx`).
2. **Review Output:** The assistant will ingest the file and evaluate the rows.
3. **Provide Globals/Fixes:** The agent will ask for parameters like `as_of` date, rounding preferences, or fixes for missing fx rates. Type your answers directly into the chat input.
4. **Download Results:** Once you finish correcting errors (or decide to skip the rest), the agent will finalize the process and provide two download buttons for `success.xlsx` and `errors.xlsx`.
