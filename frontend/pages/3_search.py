import streamlit as st
import requests

# ── Auth guard ────────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in to access this page.")
    st.info("👈 Click **login** in the sidebar.")
    st.stop()

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Search Jobs", page_icon="🔍")
st.title("🔍 Search Jobs")

FASTAPI_URL = st.secrets["FASTAPI_URL"]
token = st.session_state.jwt

# ── Guard: no resume uploaded ─────────────────────────────────
if not st.session_state.get("profile"):
    st.warning("⚠️ You haven't uploaded your resume yet.")
    st.info("Upload your resume first so we can pre-fill your role and find relevant jobs.")
    st.page_link("pages/2_upload.py", label="👈 Go to Upload Resume")
    st.stop()

# ── Pre-fill role from uploaded resume ────────────────────────
profile = st.session_state.profile
default_role = profile.get("role", "")

# ── Page intro ────────────────────────────────────────────────
st.markdown("Your resume role is pre-filled. You can change it before searching.")

with st.expander("Your current profile", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Role:** {profile.get('role', 'N/A')}")
    with col2:
        exp = profile.get("experience_years", 0)
        st.markdown(f"**Experience:** {exp} year(s)" if exp else "**Experience:** Fresher")
    st.markdown(f"**Skills:** {', '.join(profile.get('skills', []))}")

st.divider()

# ── Search form ───────────────────────────────────────────────
with st.form("search_form"):
    role = st.text_input(
        "Job Role",
        value=default_role,
        placeholder="e.g. Python Developer, Data Analyst, GenAI Engineer"
    )
    location = st.text_input(
        "Location",
        value="India",
        placeholder="e.g. Bangalore, Mumbai, Hyderabad"
    )
    submitted = st.form_submit_button("🔍 Find Jobs", use_container_width=True)

# ── On submit ─────────────────────────────────────────────────
if submitted:
    if not role.strip():
        st.error("Please enter a job role.")
        st.stop()

    if not location.strip():
        st.error("Please enter a location.")
        st.stop()

    with st.spinner(f"Searching for **{role}** jobs in **{location}**..."):
        try:
            response = requests.get(
                f"{FASTAPI_URL}/jobs",
                params={"role": role.strip(), "location": location.strip()},
                headers={"Authorization": f"Bearer {token}"},
                timeout=45
            )

            if response.status_code == 400:
                st.warning("⚠️ Please upload your resume before searching for jobs.")
                st.page_link("pages/2_upload.py", label="👈 Go to Upload Page")
                st.stop()

            elif response.status_code == 401:
                st.error("Session expired. Please log in again.")
                st.session_state.clear()
                st.switch_page("pages/1_login.py")
                st.stop()

            elif response.status_code == 503:
                st.error("Job search service is unavailable. Please try again shortly.")
                st.stop()

            elif response.status_code != 200:
                st.error(f"Something went wrong. Please try again. ({response.status_code})")
                st.stop()

            data = response.json()
            jobs = data.get("jobs", [])
            from_cache = data.get("from_cache", False)

            if not jobs:
                st.warning("No jobs found. Try a different role or broaden your location.")
                st.stop()

            # Store in session for results page
            st.session_state.jobs = jobs
            st.session_state.search_role = role.strip()
            st.session_state.search_location = location.strip()

            # Clear old results so matching re-runs with new jobs
            if "ranked_jobs" in st.session_state:
                del st.session_state.ranked_jobs
            st.session_state.show_count = 10

            # Success feedback
            cache_note = " ⚡ from cache" if from_cache else " 🌐 freshly fetched"
            st.success(f"✅ Found **{len(jobs)} jobs**{cache_note}")

            if from_cache:
                st.caption("Results loaded from cache — instant! Cache refreshes every hour.")
            else:
                st.caption("Fresh results fetched from job boards.")

            st.divider()
            st.info("Click below to let AI score each job against your resume.")

            if st.button("🎯 Match Jobs to My Resume →", use_container_width=True):
                st.switch_page("pages/4_results.py")

        except requests.exceptions.Timeout:
            st.error("Job search timed out. The API is slow right now. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Make sure FastAPI is running.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")