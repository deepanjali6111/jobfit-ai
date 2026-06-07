import streamlit as st

st.set_page_config(
    page_title="JobFit AI",
    page_icon="💼",
    layout="centered"
)

# ── Auth guard ───────────────────────────────────────────────
# Pages that don't require login
PUBLIC_PAGES = ["1_login"]

# Get current page name
current_page = st.query_params.get("page", "")

# If not logged in, show warning on protected pages
if not st.session_state.get("user_id"):
    st.title("💼 JobFit AI")
    st.warning("Please log in to access this page.")
    st.info("👈 Click **login** in the sidebar to get started.")
    st.stop()

# ── Logged in — show sidebar info + logout ───────────────────
with st.sidebar:
    st.markdown("---")
    st.caption(f"Logged in as:")
    st.caption(f"**{st.session_state.get('email', '')}**")
    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Home page content (shown after login) ────────────────────
st.title("💼 JobFit AI")
st.success("You are logged in.")
st.markdown("""
### What would you like to do?

Use the sidebar to navigate:

- 📄 **Upload Resume** — upload your PDF and extract your profile
- 🔍 **Search Jobs** — find jobs matching your skills
- 📊 **Results** — see your ranked job matches
""")