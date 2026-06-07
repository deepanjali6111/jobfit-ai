import streamlit as st
from supabase import create_client
from gotrue.errors import AuthApiError

# ── Supabase client ──────────────────────────────────────────
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

# ── Page config ──────────────────────────────────────────────
st.set_page_config(page_title="JobFit AI – Login", page_icon="🔐")
st.title("🔐 JobFit AI")
st.caption("Find jobs that match your resume using AI")

# ── Already logged in? ───────────────────────────────────────
if st.session_state.get("user_id"):
    st.success("Already logged in.")
    st.info("Use the sidebar to navigate to Resume Upload.")
    st.stop()

# ── Mode selector ────────────────────────────────────────────
mode = st.radio(
    "Choose action",
    ["Sign In", "Sign Up"],
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

# ── SIGN IN ──────────────────────────────────────────────────
if mode == "Sign In":
    st.subheader("Welcome back")

    login_email    = st.text_input("Email",    key="si_email",    placeholder="you@example.com")
    login_password = st.text_input("Password", key="si_password", placeholder="Your password", type="password")

    if st.button("Sign In", use_container_width=True):
        if not login_email or not login_password:
            st.warning("Please enter both email and password.")
        else:
            try:
                response = supabase.auth.sign_in_with_password({
                    "email":    login_email,
                    "password": login_password
                })
                st.session_state.user_id = response.user.id
                st.session_state.jwt     = response.session.access_token
                st.session_state.email   = response.user.email

                st.success("Signed in successfully!")
                st.info("Go to **Resume Upload** in the sidebar.")

            except AuthApiError as e:
                msg = str(e).lower()
                if "invalid" in msg or "credentials" in msg:
                    st.error("Incorrect email or password. Please try again.")
                elif "confirmed" in msg or "verify" in msg:
                    st.error("Please confirm your email first. Check your inbox.")
                else:
                    st.error(f"Sign in failed: {str(e)}")

# ── SIGN UP ──────────────────────────────────────────────────
elif mode == "Sign Up":
    st.subheader("Create your account")

    signup_email    = st.text_input("Email",            key="su_email",    placeholder="you@example.com")
    signup_password = st.text_input("Password",         key="su_password", placeholder="Minimum 6 characters", type="password")
    signup_confirm  = st.text_input("Confirm Password", key="su_confirm",  placeholder="Repeat your password",  type="password")

    if st.button("Create Account", use_container_width=True):
        if not signup_email or not signup_password or not signup_confirm:
            st.warning("Please fill in all fields.")
        elif signup_password != signup_confirm:
            st.error("Passwords do not match.")
        elif len(signup_password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            try:
                response = supabase.auth.sign_up({
                    "email":    signup_email,
                    "password": signup_password
                })

                # Supabase returns a user even for duplicate emails
                # but identities list is empty — detect this
                if response.user and len(response.user.identities) == 0:
                    st.error("An account with this email already exists. Please sign in instead.")
                else:
                    st.success("Account created! Please check your email to confirm, then sign in.")

            except AuthApiError as e:
                msg = str(e).lower()
                if "already" in msg or "exists" in msg:
                    st.error("An account with this email already exists. Please sign in instead.")
                else:
                    st.error(f"Sign up failed: {str(e)}")