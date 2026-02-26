import streamlit as st
import uuid
import os
import re
import base64
import json
import html as html_module
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.builder import build_graph

st.set_page_config(
    page_title="Spreadsheet Validator Agent",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS: centered title; Assistant left; User at right corner
st.markdown("""
<style>
    /* Center the main title (first h1 in main block) */
    h1 { text-align: center; }
    /* User message pushed to right corner */
    .user-msg-right { text-align: right; margin-bottom: 0.75rem; }
    .user-msg-right .chat-bubble { display: inline-block; text-align: left; max-width: 85%; }
    .user-msg-right .chat-label { margin-bottom: 0.25rem; }
    .chat-bubble { padding: 0.75rem 1rem; border-radius: 12px; }
    .user-bubble { background: rgba(151, 166, 195, 0.25); border: 1px solid var(--border-color); }
    .assistant-bubble { background: var(--secondary-background-color); border: 1px solid var(--border-color); }
    [data-testid="stBottom"] { padding-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)


def _is_tool_or_internal(content: str) -> bool:
    """Treat as internal: empty, raw JSON, file path list — don't show as assistant reply."""
    if not content or not content.strip():
        return True
    s = content.strip()
    if s.startswith("{") and ("\"rows\"" in s or "\"prompts\"" in s or "\"success_b64\"" in s or "\"errors_b64\"" in s):
        return True
    if s.startswith("[") and (r"\\" in s or "C:" in s or "/" in s):
        return True
    if re.match(r"^[A-Za-z]:[\\/]", s) or (s.startswith("/") and len(s) < 200):
        return True
    return False


def _extract_download_files_from_messages(messages) -> dict | None:
    """If the last write_output tool result is in messages, return {filename: bytes}."""
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if content is None:
            continue
        data = content
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(data, dict) or "success_b64" not in data or "errors_b64" not in data:
            continue
        try:
            return {
                "success.xlsx": base64.b64decode(data["success_b64"]),
                "errors.xlsx": base64.b64decode(data["errors_b64"]),
            }
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _messages_for_display(messages):
    """One User and one Assistant per turn; skip empty and raw tool output."""
    display = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if isinstance(msg, HumanMessage):
            display.append(("user", (msg.content or "")))
            i += 1
            continue
        if isinstance(msg, AIMessage):
            run_content = None
            j = i
            while j < len(messages) and not isinstance(messages[j], HumanMessage):
                m = messages[j]
                if isinstance(m, AIMessage):
                    c = m.content
                    c = c if isinstance(c, str) else str(c or "")
                    if not _is_tool_or_internal(c):
                        run_content = c
                else:
                    c = getattr(m, "content", str(m))
                    if c and not _is_tool_or_internal(str(c)):
                        run_content = str(c)
                j += 1
            if run_content is not None:
                display.append(("assistant", run_content))
            i = j
            continue
        i += 1
    return display


st.markdown("<h1 style='text-align: center;'>📂 Spreadsheet Validator Agent</h1>", unsafe_allow_html=True)

import shutil

# Session state
if "init_cleanup" not in st.session_state:
    st.session_state.init_cleanup = True
    if os.path.exists("runs/current"):
        shutil.rmtree("runs/current")
    os.makedirs("runs/current", exist_ok=True)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "show_upload" not in st.session_state:
    st.session_state.show_upload = False
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "download_files" not in st.session_state:
    st.session_state.download_files = None

# ---- Chat: Assistant left, User at right corner ----
display_pairs = _messages_for_display(st.session_state.messages)
for role, content in display_pairs:
    if role == "assistant":
        col_left, col_right = st.columns([5, 1])
        with col_left:
            st.markdown("**Assistant**")
            st.markdown(content)
    else:
        # Single right-aligned block so user message sits in the right corner
        escaped = html_module.escape(content).replace("\n", "<br>")
        st.markdown(
            f'<div class="user-msg-right"><div class="chat-label"><strong>User</strong></div>'
            f'<div class="chat-bubble user-bubble">{escaped}</div></div>',
            unsafe_allow_html=True,
        )

# ---- Bottom area: upload (+ icon) and chat input ----
st.markdown("---")
st.caption("Attach a file or type a message below.")

# Row: + Upload button (toggles file uploader)
col_upload, col_spacer = st.columns([1, 5])
with col_upload:
    if st.button("➕ Upload file", key="upload_btn", use_container_width=True):
        st.session_state.show_upload = not st.session_state.show_upload
        st.rerun()

if st.session_state.show_upload:
    with st.expander("📎 Upload CSV or Excel", expanded=True):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["csv", "xlsx"],
            key="file_uploader",
            label_visibility="collapsed",
        )
        if uploaded_file:
            os.makedirs("uploads", exist_ok=True)

            # Always save as a canonical "current_upload" file and replace
            # any previous upload so the ingest tool can read it without
            # needing the user to provide a path.
            original_name = uploaded_file.name
            _, ext = os.path.splitext(original_name)
            ext = ext.lower()

            if ext not in [".csv", ".xlsx"]:
                st.error("Unsupported file type. Please upload a .csv or .xlsx file.")
            else:
                canonical_path = os.path.join("uploads", f"current_upload{ext}")

                # Remove any previous canonical file of the other extension
                other_ext = ".csv" if ext == ".xlsx" else ".xlsx"
                other_path = os.path.join("uploads", f"current_upload{other_ext}")
                if os.path.exists(other_path):
                    os.remove(other_path)

                with open(canonical_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Persist canonical path in session
                st.session_state.file_path = canonical_path
                st.session_state.show_upload = False

                # Auto-start agent processing for the newly uploaded file
                auto_msg = (
                    "I have just uploaded a new spreadsheet. "
                    "Please ingest it and tell me what you need next to validate it."
                )
                st.session_state.messages.append(HumanMessage(content=auto_msg))

                with st.spinner("Processing uploaded file..."):
                    result = st.session_state.graph.invoke(
                        {
                            "messages": st.session_state.messages,
                            "file_path": st.session_state.file_path,
                        },
                        config={"configurable": {"thread_id": st.session_state.thread_id}},
                    )

                st.session_state.messages = result["messages"]
                st.session_state.download_files = _extract_download_files_from_messages(result["messages"])

                st.success(f"Uploaded **{original_name}** and started processing it.")
                st.rerun()

# Show current file if set
if st.session_state.file_path:
    st.caption(f"📄 Current file: `{os.path.basename(st.session_state.file_path)}`")

# Download buttons when validation output is available
if st.session_state.download_files:
    st.markdown("**📥 Download results**")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            label="Download success.xlsx",
            data=st.session_state.download_files["success.xlsx"],
            file_name="success.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_success",
        )
    with d2:
        st.download_button(
            label="Download errors.xlsx",
            data=st.session_state.download_files["errors.xlsx"],
            file_name="errors.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_errors",
        )

# Chat input at bottom
user_input = st.chat_input("Ask the agent to validate your file...")

if user_input:
    if not st.session_state.file_path:
        col_left, col_right = st.columns([5, 1])
        with col_left:
            st.markdown("**Assistant**")
            st.warning("Please upload a CSV or Excel file first using the **➕ Upload file** button above.")
        st.stop()

    # Append user message and show in UI immediately
    st.session_state.messages.append(HumanMessage(content=user_input))

    # Invoke graph with full conversation history (and persisted thread for checkpointer)
    with st.spinner("Thinking..."):
        result = st.session_state.graph.invoke(
            {
                "messages": st.session_state.messages,
                "file_path": st.session_state.file_path,
            },
            config={"configurable": {"thread_id": st.session_state.thread_id}},
        )

    # Update conversation from graph output (includes new assistant reply)
    st.session_state.messages = result["messages"]
    st.session_state.download_files = _extract_download_files_from_messages(result["messages"])

    st.rerun()
