import streamlit as st

from api_client import APIError, chat, reset_chat
from auth_widget import handle_session_expired, render_auth_sidebar

st.set_page_config(page_title="Chat - MasaStore", page_icon="💬", layout="wide")
st.title("💬 Chat assistant")

render_auth_sidebar()

if not st.session_state.get("token"):
    st.warning("Please log in to use the chat.")
    st.stop()

st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("prompts_left", 5)

col_info, col_reset = st.columns([3, 1])
with col_info:
    st.caption(
        f"💡 **{st.session_state.prompts_left}** prompts left this session. "
        f"Ask about our products in any language."
    )
with col_reset:
    if st.button("🔄 Reset chat", use_container_width=True):
        try:
            reset_chat(st.session_state.token)
            st.session_state.chat_history = []
            st.session_state.prompts_left = 5
            st.toast("Chat reset")
            st.rerun()
        except APIError as e:
            if e.is_auth_expired():
                handle_session_expired()
            st.error(f"Reset failed: {e.message}")

st.divider()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if st.session_state.prompts_left > 0:
    user_msg = st.chat_input("Ask about our products...", max_chars=300)
    if user_msg:
        try:
            response = chat(
                user_msg,
                st.session_state.chat_history,
                st.session_state.token,
            )
            st.session_state.chat_history.append({"role": "user", "content": user_msg})
            st.session_state.chat_history.append(
                {"role": "assistant", "content": response["assistant_message"]}
            )
            st.session_state.prompts_left = response["prompts_left"]
            st.rerun()
        except APIError as e:
            if e.is_auth_expired():
                handle_session_expired()
            elif e.is_rate_limited() and e.message.startswith("Daily"):
                st.warning(f"⚠️ {e.message}")
            elif e.is_rate_limited():
                st.warning(
                    "⚠️ You've reached the 5-message limit. "
                    "Click 'Reset chat' to start over."
                )
            else:
                st.error(f"❌ {e.message}")
else:
    st.warning(
        "⚠️ You've reached the 5-message limit for this session. "
        "Click **🔄 Reset chat** above to start over."
    )
