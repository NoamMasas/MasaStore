import streamlit as st

from api_client import (
    APIError,
    add_favorite,
    add_to_cart,
    get_all_items,
    get_favorites,
    get_recommendations,
    remove_favorite,
    search_items,
)
from auth_widget import handle_session_expired, render_auth_sidebar

st.set_page_config(page_title="MasaStore", page_icon="🛒", layout="wide")
st.title("🛒 MasaStore")

render_auth_sidebar()

OPERATOR_LABELS = {
    "—": "—",
    "lt": "< less than",
    "gt": "> greater than",
    "eq": "= equal",
}

with st.form("search_form"):
    st.subheader("Search & filter")
    name = st.text_input(
        "Name", placeholder="e.g. mouse, or sun, ball (comma for multi-keyword)"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Price filter**")
        sub1, sub2 = st.columns([1, 1])
        with sub1:
            price_op = st.selectbox(
                "Price operator",
                options=["—", "lt", "gt", "eq"],
                format_func=lambda x: OPERATOR_LABELS[x],
                label_visibility="collapsed",
                key="price_op_select",
            )
        with sub2:
            price_value = st.number_input(
                "Price value",
                min_value=0.0,
                value=0.0,
                step=1.0,
                label_visibility="collapsed",
            )
    with col2:
        st.write("**Stock filter**")
        sub3, sub4 = st.columns([1, 1])
        with sub3:
            stock_op = st.selectbox(
                "Stock operator",
                options=["—", "lt", "gt", "eq"],
                format_func=lambda x: OPERATOR_LABELS[x],
                label_visibility="collapsed",
                key="stock_op_select",
            )
        with sub4:
            stock_value = st.number_input(
                "Stock value",
                min_value=0,
                value=0,
                step=1,
                label_visibility="collapsed",
            )

    submitted = st.form_submit_button("🔍 Search")

has_filters = bool(name) or price_op != "—" or stock_op != "—"

try:
    if has_filters:
        items = search_items(
            name=name or None,
            stock_op=stock_op if stock_op != "—" else None,
            stock_value=int(stock_value) if stock_op != "—" else None,
            price_op=price_op if price_op != "—" else None,
            price_value=float(price_value) if price_op != "—" else None,
        )
    else:
        items = get_all_items()
except APIError as e:
    st.error(f"⚠️ {e.message}")
    items = []

logged_in = bool(st.session_state.get("token"))
favorited_ids: set[int] = set()
favorite_id_by_item: dict[int, int] = {}

if logged_in:
    try:
        favs = get_favorites(st.session_state.user_id, st.session_state.token)
        favorited_ids = {f["item_id"] for f in favs}
        favorite_id_by_item = {f["item_id"]: f["id"] for f in favs}
    except APIError as e:
        if e.is_auth_expired():
            handle_session_expired()
        # else: silently skip the favorites overlay; the items still display.


def _toggle_favorite(item_id: int, item_name: str, is_currently_fav: bool):
    try:
        if is_currently_fav:
            remove_favorite(favorite_id_by_item[item_id], st.session_state.token)
            st.toast(f"Removed {item_name} from favorites")
        else:
            add_favorite(item_id, st.session_state.token)
            st.toast(f"❤️ Added {item_name} to favorites")
        st.rerun()
    except APIError as e:
        if e.is_auth_expired():
            handle_session_expired()
        st.error(e.message)


def _add_to_cart_action(item_id: int, item_name: str, qty: int):
    try:
        order = add_to_cart(item_id, qty, st.session_state.token)
        new_total = next(
            (line["quantity"] for line in order.get("items", []) if line["item_id"] == item_id),
            qty,
        )
        st.toast(f"🛒 Added {qty} × {item_name} — {new_total} now in cart")
    except APIError as e:
        if e.is_auth_expired():
            handle_session_expired()
        st.error(e.message)


# Outside the search form so re-ordering doesn't require a Search resubmit.
SORT_OPTIONS = {
    "name_asc":   "Name (A-Z)",
    "price_asc":  "Price (low to high)",
    "price_desc": "Price (high to low)",
    "stock_desc": "Stock (high to low)",
    "stock_asc":  "Stock (low to high)",
}
if logged_in:
    SORT_OPTIONS = {"for_you": "✨ For You", **SORT_OPTIONS}

sort_choice = st.selectbox(
    "Sort by",
    options=list(SORT_OPTIONS.keys()),
    format_func=lambda k: SORT_OPTIONS[k],
)

ranking_map: dict[int, int] = {}
if sort_choice == "for_you":
    try:
        rec_resp = get_recommendations(st.session_state.token)
        ranking_map = {
            r["item_id"]: i
            for i, r in enumerate(rec_resp.get("recommendations", []))
        }
    except APIError as e:
        if e.is_auth_expired():
            handle_session_expired()
        st.warning("Recommendations unavailable — falling back to name sort.")
        sort_choice = "name_asc"


def _sort_key(it):
    if sort_choice == "name_asc":
        return it["item_name"].lower()
    if sort_choice == "price_asc":
        return float(it["price"])
    if sort_choice == "price_desc":
        return -float(it["price"])
    if sort_choice == "stock_desc":
        return -int(it["stock"])
    if sort_choice == "stock_asc":
        return int(it["stock"])
    if sort_choice == "for_you":
        # Unranked items sink to the bottom.
        return ranking_map.get(it["id"], 10**9)
    return 0


# Two-pass stable sort: primary key first, then push out-of-stock to the bottom.
items.sort(key=_sort_key)
items.sort(key=lambda i: i["stock"] == 0)


if items:
    st.write(f"**{len(items)} item(s) found**")
    for item in items:
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.subheader(item["item_name"])
                st.write(f"💰 **${item['price']}**")
            with col_b:
                if item["stock"] == 0:
                    st.error("Out of stock")
                else:
                    st.success(f"In stock: {item['stock']}")

            if logged_in:
                is_fav = item["id"] in favorited_ids
                fav_label = "❤️ Favorited" if is_fav else "🤍 Favorite"

                col_fav, col_cart = st.columns(2)
                with col_fav:
                    if st.button(
                        fav_label,
                        key=f"fav_{item['id']}",
                        use_container_width=True,
                    ):
                        _toggle_favorite(item["id"], item["item_name"], is_fav)
                with col_cart:
                    with st.popover(
                        "🛒 Add to cart",
                        use_container_width=True,
                        disabled=item["stock"] == 0,
                    ):
                        qty = st.number_input(
                            "Quantity",
                            min_value=1,
                            max_value=max(1, item["stock"]),
                            value=1,
                            step=1,
                            key=f"qty_main_{item['id']}",
                        )
                        if st.button("Add", key=f"add_{item['id']}"):
                            _add_to_cart_action(item["id"], item["item_name"], int(qty))
elif has_filters:
    st.warning("No items match your filters. Try broadening the search.")
else:
    st.info("No items in the catalog yet.")
