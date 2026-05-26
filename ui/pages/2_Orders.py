import streamlit as st

from api_client import (
    APIError,
    delete_order,
    get_orders,
    purchase,
    remove_cart_item,
    update_cart_item,
)
from auth_widget import handle_session_expired, render_auth_sidebar

st.set_page_config(page_title="Orders - MasaStore", page_icon="🛒", layout="wide")
st.title("🛒 Orders")

render_auth_sidebar()

if not st.session_state.get("token"):
    st.warning("Please log in to see your orders.")
    st.stop()

try:
    orders = get_orders(st.session_state.user_id, st.session_state.token)
except APIError as e:
    if e.is_auth_expired():
        handle_session_expired()
    st.error(f"Failed to load orders: {e.message}")
    st.stop()


def _on_api_error(e: APIError, prefix: str):
    if e.is_auth_expired():
        handle_session_expired()
    st.error(f"{prefix}: {e.message}")


temp_order = next((o for o in orders if o["status"] == "TEMP"), None)
close_orders = [o for o in orders if o["status"] == "CLOSE"]


st.subheader("🛒 Active Cart")

if temp_order is None:
    st.info("Your cart is empty. Browse items on the home page to add some.")
else:
    with st.container(border=True):
        col_total, col_address = st.columns([1, 2])
        with col_total:
            st.metric("Total", f"${temp_order['total_price']}")
        with col_address:
            st.write(f"📍 **Shipping to:** {temp_order['shipping_address']}")

        st.divider()

        for item in temp_order["items"]:
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                st.write(f"**{item['item_name']}**")
                st.caption(f"${item['price']} per unit")
            with col_b:
                new_qty = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=item["quantity"],
                    step=1,
                    key=f"qty_{item['item_id']}",
                    label_visibility="collapsed",
                )
                if new_qty != item["quantity"]:
                    if st.button(
                        "Update",
                        key=f"upd_{item['item_id']}",
                        use_container_width=True,
                    ):
                        try:
                            update_cart_item(
                                item["item_id"],
                                int(new_qty),
                                st.session_state.token,
                            )
                            st.toast("Quantity updated")
                            st.rerun()
                        except APIError as e:
                            _on_api_error(e, "Update failed")
            with col_c:
                if st.button(
                    "❌ Remove",
                    key=f"rm_{item['item_id']}",
                    use_container_width=True,
                ):
                    try:
                        remove_cart_item(
                            temp_order["id"],
                            item["item_id"],
                            st.session_state.token,
                        )
                        st.toast(f"Removed {item['item_name']}")
                        st.rerun()
                    except APIError as e:
                        _on_api_error(e, "Remove failed")

        st.divider()
        col_pay, col_del = st.columns(2)
        with col_pay:
            if st.button(
                "💳 Purchase",
                type="primary",
                use_container_width=True,
            ):
                try:
                    purchase(temp_order["id"], st.session_state.token)
                    st.success("✅ Order purchased! Thank you.")
                    st.rerun()
                except APIError as e:
                    _on_api_error(e, "Purchase failed")
        with col_del:
            if st.button("🗑️ Delete entire cart", use_container_width=True):
                try:
                    delete_order(temp_order["id"], st.session_state.token)
                    st.success("Cart deleted")
                    st.rerun()
                except APIError as e:
                    _on_api_error(e, "Delete failed")


st.subheader(f"📜 Order History ({len(close_orders)})")

if not close_orders:
    st.caption("No past orders yet.")
else:
    for order in close_orders:
        header = (
            f"Order #{order['id']} — "
            f"${order['total_price']} — "
            f"{order['created_at'][:10]}"
        )
        with st.expander(header):
            st.caption(f"Shipped to: {order['shipping_address']}")
            for item in order["items"]:
                st.write(
                    f"- **{item['item_name']}** × {item['quantity']} "
                    f"@ ${item['price']}"
                )
