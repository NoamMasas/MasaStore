import streamlit as st

from api_client import APIError, get_favorites, remove_favorite
from auth_widget import handle_session_expired, render_auth_sidebar

st.set_page_config(page_title="Favorites - MasaStore", page_icon="❤️", layout="wide")
st.title("❤️ My Favorites")

render_auth_sidebar()

if not st.session_state.get("token"):
    st.warning("Please log in to see your favorites.")
    st.stop()

try:
    favorites = get_favorites(st.session_state.user_id, st.session_state.token)
except APIError as e:
    if e.is_auth_expired():
        handle_session_expired()
    st.error(f"Failed to load favorites: {e.message}")
    st.stop()

if not favorites:
    st.info("You haven't favorited anything yet. Browse items on the home page.")
else:
    st.write(f"**{len(favorites)} favorite(s)**")
    for fav in favorites:
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([3, 1, 1])
            with col_a:
                st.subheader(fav["item_name"])
                st.write(f"💰 **${fav['price']}**")
            with col_b:
                if fav["stock"] == 0:
                    st.error("Out of stock")
                else:
                    st.success(f"In stock: {fav['stock']}")
            with col_c:
                if st.button("❌ Remove", key=f"rm_{fav['id']}", use_container_width=True):
                    try:
                        remove_favorite(fav["id"], st.session_state.token)
                        st.toast("Removed from favorites")
                        st.rerun()
                    except APIError as e:
                        if e.is_auth_expired():
                            handle_session_expired()
                        st.error(f"Failed to remove: {e.message}")
