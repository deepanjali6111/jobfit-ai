import streamlit as st
import requests

# ── Auth guard ───────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in to access this page.")
    st.info("👈 Click **login** in the sidebar.")
    st.stop()

# ── Page config ──────────────────────────────────────────────
st.title("📄 Upload Resume")
st.caption("Upload your PDF resume and we'll extract your profile automatically.")

FASTAPI_URL = st.secrets["FASTAPI_URL"]

# ── Show current profile if exists ──────────────────────────
if st.session_state.get("profile"):
    profile = st.session_state.profile
    st.success("✅ Resume already uploaded.")

    with st.expander("Your current profile — click to view", expanded=False):
        st.markdown(f"**Role:** {profile['role']}")
        st.markdown(f"**Experience:** {profile['experience_years']} year(s)")
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

                    # Store profile in session for other pages to use
                    st.session_state.profile = {
                        "skills":           data["skills"],
                        "role":             data["role"],
                        "experience_years": data["experience_years"]
                    }

                    # Show success message
                    st.success(data["message"])
                    st.divider()

                    # Show extracted profile
                    st.subheader("Your Extracted Profile")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Detected Role", data["role"])
                    with col2:
                        st.metric(
                            "Experience",
                            f"{data['experience_years']} yr(s)" if data["experience_years"] > 0 else "Fresher"
                        )

                    st.markdown("**Extracted Skills:**")
                    skills_display = "  ".join([f"`{skill}`" for skill in data["skills"]])
                    st.markdown(skills_display)

                    st.divider()
                    st.info("✅ Profile saved. Go to **Search Jobs** in the sidebar to find matching jobs.")

                elif response.status_code == 422:
                    st.error(f"Invalid file: {response.json()['detail']}")

                elif response.status_code == 503:
                    st.error(response.json()["detail"])

                else:
                    st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")

            except requests.exceptions.Timeout:
                st.error("Request timed out. The AI is taking too long. Please try again.")

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure FastAPI is running on port 8000.")