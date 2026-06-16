import streamlit as st
import requests

# ── Auth guard ────────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in to access this page.")
    st.info("👈 Click **login** in the sidebar.")
    st.stop()

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Job Results", page_icon="🎯")
st.title("🎯 Your Job Matches")

FASTAPI_URL = st.secrets["FASTAPI_URL"]
token = st.session_state.jwt

# ── Guard: no jobs in session ─────────────────────────────────
if "jobs" not in st.session_state or not st.session_state.jobs:
    st.warning("No jobs to match. Please search for jobs first.")
    st.page_link("pages/3_search.py", label="👈 Go to Search Page")
    st.stop()

# ── Run matching if not already done ─────────────────────────
if "ranked_jobs" not in st.session_state:
    st.info("🤖 AI is scoring your jobs against your resume. This takes 2-3 minutes for 10 jobs.")
    progress = st.progress(0, text="Starting AI scoring...")

    try:
        progress.progress(10, text="Sending jobs to Gemini...")

        response = requests.post(
            f"{FASTAPI_URL}/match",
            json={"jobs": st.session_state.jobs},
            headers={"Authorization": f"Bearer {token}"},
            timeout=600  # 10 minutes max
        )

        progress.progress(90, text="Processing results...")

        if response.status_code == 404:
            st.warning("No resume profile found. Please upload your resume first.")
            st.page_link("pages/2_upload.py", label="👈 Go to Upload Page")
            st.stop()

        elif response.status_code == 503:
            st.error(response.json().get("detail", "AI quota reached. Please try again later."))
            st.stop()

        elif response.status_code != 200:
            st.error(f"Something went wrong. ({response.status_code})")
            st.stop()

        data = response.json()
        st.session_state.ranked_jobs = data.get("ranked_jobs", [])
        progress.progress(100, text="Done!")

    except requests.exceptions.Timeout:
        st.error("⏱️ Scoring is taking longer than expected.")
        st.warning("Your results may still be processing. Wait 30 seconds then click Retry.")
        if st.button("🔄 Retry — Load Results", use_container_width=True):
            st.rerun()
        st.stop()

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")
        st.stop()

    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

# ── Display results ───────────────────────────────────────────
ranked_jobs = st.session_state.ranked_jobs

if not ranked_jobs:
    st.warning("No matches found. Try searching with a different role or location.")
    st.page_link("pages/3_search.py", label="👈 Back to Search")
    st.stop()

# Show search context
role = st.session_state.get("search_role", "")
location = st.session_state.get("search_location", "")
if role and location:
    st.caption(f"Showing results for **{role}** in **{location}**")

st.divider()

# ── How many to show ──────────────────────────────────────────
if "show_count" not in st.session_state:
    st.session_state.show_count = 10

jobs_to_show = ranked_jobs[:st.session_state.show_count]

# ── Job cards ─────────────────────────────────────────────────
for i, job in enumerate(jobs_to_show):
    score = job.get("match_score", 0)
    title = job.get("title", "Unknown Title")
    company = job.get("company", "Unknown Company")
    location_job = job.get("location", "")
    url = job.get("url", "")
    matching = job.get("matching_skills", [])
    missing = job.get("missing_skills", [])
    source = job.get("source", "")

    # Score color
    if score >= 80:
        score_color = "🟢"
    elif score >= 60:
        score_color = "🟡"
    elif score >= 40:
        score_color = "🟠"
    else:
        score_color = "🔴"

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"### {i + 1}. {title}")
            st.markdown(f"🏢 **{company}** · 📍 {location_job} · 🔗 *{source}*")
        with col2:
            st.markdown(f"## {score_color} {score}%")

        if matching:
            st.markdown(
                "✅ **Matching skills:** " +
                " ".join([f"`{s}`" for s in matching])
            )

        if missing:
            st.markdown(
                "❌ **Missing skills:** " +
                " ".join([f"`{s}`" for s in missing])
            )

        if url:
            st.link_button("Apply Now →", url, use_container_width=True)
        else:
            st.button("No link available", disabled=True,
                      use_container_width=True, key=f"no_link_{i}")

        st.divider()

# ── Load more ─────────────────────────────────────────────────
if st.session_state.show_count < len(ranked_jobs):
    remaining = len(ranked_jobs) - st.session_state.show_count
    if st.button(
        f"Load {min(10, remaining)} more results ↓",
        use_container_width=True
    ):
        st.session_state.show_count += 10
        st.rerun()
else:
    st.caption(f"Showing all {len(ranked_jobs)} results.")

# ── New search button ─────────────────────────────────────────
st.divider()
if st.button("🔍 New Search", use_container_width=True):
    del st.session_state.ranked_jobs
    st.session_state.show_count = 10
    st.switch_page("pages/3_search.py")