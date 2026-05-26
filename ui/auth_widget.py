import streamlit as st
from jose import jwt

from api_client import APIError, login, register

# Mirror of model/user_request.py SUPPORTED_COUNTRIES — keep in sync.
SUPPORTED_COUNTRIES = {
    "IL": "Israel",
    "US": "United States",
    "UK": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "ES": "Spain",
    "IT": "Italy",
    "JP": "Japan",
    "BR": "Brazil",
    "IN": "India",
}


def _decode_token(token: str) -> tuple[int, str]:
    # No signature verification: the server already signed it; this read is
    # for display only (username + id) and never grants access.
    payload = jwt.decode(token, key="", options={"verify_signature": False})
    return payload["id"], payload["subject"]


def _clear_session():
    for key in ("token", "user_id", "username", "chat_history", "prompts_left"):
        st.session_state.pop(key, None)


def render_auth_sidebar():
    with st.sidebar:
        if st.session_state.get("token"):
            _render_logged_in()
        else:
            _render_login_or_register()


def _render_logged_in():
    st.success(f"Logged in as **{st.session_state.username}**")
    if st.button("Logout"):
        _clear_session()
        st.rerun()


def _render_login_or_register():
    mode = st.radio("Account", ["Login", "Register"], horizontal=True)
    if mode == "Login":
        _render_login_form()
    else:
        _render_register_form()


def _render_login_form():
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if not username or not password:
                st.error("Username and password required")
                return
            try:
                token = login(username, password)
                uid, uname = _decode_token(token)
                st.session_state.token = token
                st.session_state.user_id = uid
                st.session_state.username = uname
                st.success("Logged in!")
                st.rerun()
            except APIError as e:
                st.error(f"Login failed: {e.message}")


def _render_register_form():
    with st.form("register_form"):
        username = st.text_input("Username")
        first_name = st.text_input("First name")
        last_name = st.text_input("Last name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        country = st.selectbox(
            "Country",
            options=list(SUPPORTED_COUNTRIES.keys()),
            format_func=lambda code: f"{SUPPORTED_COUNTRIES[code]} ({code})",
        )
        city = st.text_input("City")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Register"):
            try:
                register(username, first_name, last_name, email, phone, country, city, password)
                st.success("Registered! Switch to Login.")
            except APIError as e:
                st.error(f"Registration failed: {e.message}")


def handle_session_expired():
    _clear_session()
    st.warning("Session expired. Please log in again.")
    st.stop()
