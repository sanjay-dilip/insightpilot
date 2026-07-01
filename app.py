# Entry point for the InsightPilot Streamlit web app
from pathlib import Path

import streamlit as st

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


def resolve_input() -> None:
    """Determine which data source is active and update session state.

    Precedence rule: an uploaded file always wins over a sample selection.
    Uploading is the more deliberate, more recent user action, so if a user
    uploads a file after previously picking a sample (or vice versa), the
    upload should not be silently ignored in favor of a stale dropdown
    value. If no upload is present, fall back to the selected sample.
    """
    uploaded_file = st.session_state.get("uploaded_file")
    selected_sample = st.session_state.get("selected_sample", NO_SAMPLE_SELECTED)

    if uploaded_file is not None:
        st.session_state.resolved_input = uploaded_file
        st.session_state.file_selected = True
    elif selected_sample != NO_SAMPLE_SELECTED:
        st.session_state.resolved_input = SAMPLE_DATASETS_DIR / selected_sample
        st.session_state.file_selected = True
    else:
        st.session_state.resolved_input = None
        st.session_state.file_selected = False


init_session_state()
render_sidebar()
resolve_input()

st.title("InsightPilot")

report_placeholder = st.empty()
if not st.session_state.file_selected:
    report_placeholder.write("Upload a CSV or choose a sample dataset from the sidebar to get started.")
else:
    report_placeholder.write("Report will render here in a later task.")
