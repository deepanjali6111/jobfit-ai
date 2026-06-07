import streamlit as st

# ── Auth guard ───────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in to access this page.")
    st.info("👈 Click **login** in the sidebar.")
    st.stop()

# ── Page content (placeholder until Milestone 2) ─────────────
st.title("📄 Upload Resume")
st.info("Resume upload coming in Milestone 2.")