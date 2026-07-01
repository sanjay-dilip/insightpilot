# Entry point for the InsightPilot Streamlit web app
import hashlib
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.data_profiler import profile_dataset

load_dotenv()

SAMPLE_DATASETS_DIR = Path("data/sample_datasets")
NO_SAMPLE_SELECTED = "None"

st.set_page_config(page_title="InsightPilot", layout="wide")


def get_sample_datasets(directory: Path) -> list[str]:
    """Return sorted CSV filenames available in the sample datasets directory.

    Args:
        directory: Path to the sample datasets folder.

    Returns:
        Sorted list of CSV filenames found in `directory`. Empty list if the
        directory does not exist or contains no CSV files.
    """
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.glob("*.csv"))


def init_session_state() -> None:
    """Initialize session state keys used to track the resolved data input.

    Guarded so reruns don't clobber state set by prior widget interactions.
    """
    if "resolved_input" not in st.session_state:
        st.session_state.resolved_input = None
    if "file_selected" not in st.session_state:
        st.session_state.file_selected = False


def render_sidebar() -> None:
    """Render the sidebar data-input controls (file upload and sample picker)."""
    st.sidebar.header("Data Input")
    st.sidebar.file_uploader("Upload a CSV file", type=["csv"], key="uploaded_file")

    sample_names = get_sample_datasets(SAMPLE_DATASETS_DIR)
    st.sidebar.selectbox(
        "Or choose a sample dataset",
        options=[NO_SAMPLE_SELECTED] + sample_names,
        key="selected_sample",
    )


def _save_uploaded_file(uploaded_file) -> str:
    """Persist an uploaded file to a content-hashed temp path and return its path.

    profile_dataset/run_agent require a real filesystem path (both eventually
    check os.path.exists on their argument), so an in-memory upload has to be
    written to disk first. The SHA-256 digest of the file's bytes is used as
    the filename so repeat uploads of identical content reuse the same file
    instead of writing duplicates, and that same digest is what gets used as
    the st.cache_data key for this input — not the UploadedFile object
    itself, which isn't a reliable cache key across reruns.
    """
    file_bytes = uploaded_file.getvalue()
    digest = hashlib.sha256(file_bytes).hexdigest()
    temp_path = Path(tempfile.gettempdir()) / f"insightpilot_upload_{digest}.csv"
    if not temp_path.exists():
        temp_path.write_bytes(file_bytes)
    return str(temp_path)


def resolve_input() -> None:
    """Determine which data source is active and update session state.

    Precedence rule: an uploaded file always wins over a sample selection.
    Uploading is the more deliberate, more recent user action, so if a user
    uploads a file after previously picking a sample (or vice versa), the
    upload should not be silently ignored in favor of a stale dropdown
    value. If no upload is present, fall back to the selected sample.

    `resolved_input` is always a filesystem path string (never the raw
    UploadedFile object) so downstream cached functions have one consistent,
    reliably-hashable key regardless of input source.
    """
    uploaded_file = st.session_state.get("uploaded_file")
    selected_sample = st.session_state.get("selected_sample", NO_SAMPLE_SELECTED)

    if uploaded_file is not None:
        st.session_state.resolved_input = _save_uploaded_file(uploaded_file)
        st.session_state.file_selected = True
    elif selected_sample != NO_SAMPLE_SELECTED:
        st.session_state.resolved_input = str(SAMPLE_DATASETS_DIR / selected_sample)
        st.session_state.file_selected = True
    else:
        st.session_state.resolved_input = None
        st.session_state.file_selected = False


@st.cache_data(show_spinner=False)
def get_profile(csv_path: str) -> dict:
    """Return the profiling dict for csv_path, computed once per unique path.

    Deterministic and free — cached separately from get_agent_report so a
    profile-only need never triggers a Gemini call.
    """
    return profile_dataset(csv_path)


@st.cache_data(show_spinner=False)
def get_agent_report(csv_path: str):
    """Return the AgentReport for csv_path, computed once per unique path.

    Calls Gemini via run_agent — cached separately from get_profile so this
    (paid, non-deterministic) step isn't bundled with the plain profiling
    step in a single cache entry.
    """
    from src.agent import run_agent

    return run_agent(csv_path)


init_session_state()
render_sidebar()
resolve_input()

st.title("InsightPilot")

report_placeholder = st.empty()
if not st.session_state.file_selected:
    report_placeholder.write("Upload a CSV or choose a sample dataset from the sidebar to get started.")
else:
    report_placeholder.write("Report will render here in a later task.")
