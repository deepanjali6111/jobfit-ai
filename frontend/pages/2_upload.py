import streamlit as st
import requests

# ── Auth guard ───────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in to access this page.")
    st.info("👈 Click **login** in the sidebar.")
    st.stop()

# ── Page config ──────────────────────────────────────────────
st.set_page_config(page_title="Upload Resume", page_icon="📄")
st.title("📄 Upload Resume")
st.caption("Upload your PDF resume and we'll extract your profile automatically.")

FASTAPI_URL = st.secrets["FASTAPI_URL"]


def format_experience(years) -> str:
    """Convert experience number to human readable string."""
    if years is None or years == 0:
        return "Fresher"
    elif years < 1:
        months = round(years * 12)
        return f"{months} month(s)"
    elif years == 1:
        return "1 year"
    elif years % 1 == 0:
        return f"{int(years)} years"
    else:
        full_years = int(years)
        months = round((years - full_years) * 12)
        if months == 0:
            return f"{full_years} years"
        return f"{full_years} year(s) {months} month(s)"


# ── Show current profile if exists ──────────────────────────
if st.session_state.get("profile"):
    profile = st.session_state.profile
    st.success("✅ Resume already uploaded.")

    with st.expander("Your current profile — click to view", expanded=False):
        st.markdown(f"**Role:** {profile['role']}")
        st.markdown(f"**Experience:** {format_experience(profile.get('experience_years', 0))}")
        st.markdown(f"**Skills:** {', '.join(profile['skills'])}")

    st.divider()
    st.markdown("Upload a new resume below to replace your current profile.")

# ── File uploader ────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Choose your resume PDF",
    type=["pdf"],
    help="Maximum file size: 10MB"
)

if uploaded_file is not None:
    # File size check — 10MB max
    if uploaded_file.size > 10 * 1024 * 1024:
        st.error("File too large. Please upload a PDF under 10MB.")
        st.stop()

    st.info(f"File selected: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    if st.button("Upload and Extract Profile", use_container_width=True):
        with st.spinner("Extracting text and analyzing your resume with AI..."):
            try:
                response = requests.post(
                    f"{FASTAPI_URL}/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    headers={"Authorization": f"Bearer {st.session_state.jwt}"},
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()

                    # Store profile in session for other pages
                    st.session_state.profile = {
                        "skills":           data["skills"],
                        "role":             data["role"],
                        "experience_years": data["experience_years"]
                    }

                    # Clear old results when resume changes
                    if "ranked_jobs" in st.session_state:
                        del st.session_state.ranked_jobs
                    if "jobs" in st.session_state:
                        del st.session_state.jobs

                    st.success(data["message"])
                    st.divider()

                    st.subheader("Your Extracted Profile")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Detected Role", data["role"])
                    with col2:
                        st.metric(
                            "Experience",
                            format_experience(data.get("experience_years", 0))
                        )

                    st.markdown("**Extracted Skills:**")
                    skills_display = "  ".join([f"`{skill}`" for skill in data["skills"]])
                    st.markdown(skills_display)

                    st.divider()
                    st.info("✅ Profile saved. Go to **Search Jobs** in the sidebar.")

                elif response.status_code == 422:
                    st.error(f"Invalid file: {response.json()['detail']}")

                elif response.status_code == 401:
                    st.error("Session expired. Please log in again.")
                    st.session_state.clear()
                    st.switch_page("pages/1_login.py")

                elif response.status_code == 503:
                    st.error(response.json()["detail"])

                else:
                    st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")

            except requests.exceptions.Timeout:
                st.error("Request timed out. The AI is taking too long. Please try again.")

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure FastAPI is running on port 8000.")

            except Exception as e:
                st.error(f"Unexpected error: {e}")