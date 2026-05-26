from typing import List, Optional

from exceptions.exception import (
    empty_cart_exception,
    insufficient_stock_exception,
    invalid_quantity_exception,
    item_not_found_exception,
    not_authorized_exception,
    order_already_closed_exception,
    order_item_not_found_exception,
    order_not_found_exception,
    out_of_stock_exception,
)
from model.order import Order
from model.order_request import OrderItemAddRequest
from model.order_response import OrderItemDetail, OrderResponse
from model.order_status import OrderStatus
from model.user_response import UserResponse
from repository import item_repository, order_item_repository, order_repository
from repository.database import database
from service import recommendation_service


async def _build_order_response(order_id: int) -> OrderResponse:
    order = await order_repository.get_by_id(order_id)
    if order is None:
        raise order_not_found_exception()
    items = await order_item_repository.get_items_for_order(order_id)
    # TEMP totals are recomputed on read so the line totals always add up to
    # the displayed total, even if catalog prices changed since last mutation.
    if order.status == OrderStatus.TEMP:
        total_price = await order_repository.recalculate_total_price(order_id)
    else:
        total_price = order.total_price
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        shipping_address=order.shipping_address,
        total_price=total_price,
        status=order.status,
        items=[OrderItemDetail(**row) for row in items],
    )


async def _get_or_create_temp_order(auth_user: UserResponse) -> Order:
    existing = await order_repository.get_temp_order_by_user(auth_user.id)
    if existing is not None:
        return existing
    shipping_address = f"{auth_user.city}, {auth_user.country}"
    new_id = await order_repository.create(auth_user.id, shipping_address)
    return await order_repository.get_by_id(new_id)


async def get_user_orders(user_id: int, auth_user: UserResponse) -> List[OrderResponse]:
    if auth_user.id != user_id:
        raise not_authorized_exception()
    orders = await order_repository.get_orders_by_user(user_id)
    responses: List[OrderResponse] = []
    for order in orders:
        responses.append(await _build_order_response(order.id))
    return responses


async def get_order_by_id(order_id: int, auth_user: UserResponse) -> OrderResponse:
    order = await order_repository.get_by_id(order_id)
    # Mask "not yours" as "not found" to avoid leaking other users' ids.
    if order is None or order.user_id != auth_user.id:
        raise order_not_found_exception()
    return await _build_order_response(order_id)


async def add_item_to_cart(
    request: OrderItemAddRequest, auth_user: UserResponse
) -> OrderResponse:
    if request.quantity <= 0:
        raise invalid_quantity_exception()

    item = await item_repository.get_item_by_id(request.item_id)
    if item is None:
        raise item_not_found_exception()
    if item.stock == 0:
        raise out_of_stock_exception(item.item_name)

    order = await _get_or_create_temp_order(auth_user)

    # Cumulative add — stock check uses the post-add total, not the increment.
    existing_line = await order_item_repository.get_one(order.id, request.item_id)
    existing_qty = existing_line.quantity if existing_line else 0
    new_qty = existing_qty + request.quantity

    if item.stock < new_qty:
        raise insufficient_stock_exception(item.item_name, item.stock, new_qty)

    async with database.transaction():
        if existing_line is not None:
            # Existing line: only the quantity changes — the price snapshot
            # captured at the first add is preserved.
            await order_item_repository.update_quantity(
                order.id, request.item_id, new_qty
            )
        else:
            await order_item_repository.add(
                order.id, request.item_id, new_qty, item.price
            )
        new_total = await order_repository.recalculate_total_price(order.id)
        await order_repository.update_total_price(order.id, new_total)

    recommendation_service.invalidate_user_recommendations(auth_user.id)
    return await _build_order_response(order.id)


async def update_item_in_cart(
    request: OrderItemAddRequest, auth_user: UserResponse
) -> OrderResponse:
    if request.quantity <= 0:
        raise invalid_quantity_exception()

    item = await item_repository.get_item_by_id(request.item_id)
    if item is None:
        raise item_not_found_exception()
    if item.stock == 0:
        raise out_of_stock_exception(item.item_name)
    if item.stock < request.quantity:
        raise insufficient_stock_exception(item.item_name, item.stock, request.quantity)

    order = await order_repository.get_temp_order_by_user(auth_user.id)
    if order is None:
        raise order_not_found_exception()

    existing_line = await order_item_repository.get_one(order.id, request.item_id)
    if existing_line is None:
        raise order_item_not_found_exception()

    async with database.transaction():
        await order_item_repository.update_quantity(
            order.id, request.item_id, request.quantity
        )
        new_total = await order_repository.recalculate_total_price(order.id)
        await order_repository.update_total_price(order.id, new_total)

    recommendation_service.invalidate_user_recommendations(auth_user.id)
    return await _build_order_response(order.id)


async def remove_item_from_cart(
    order_id: int, item_id: int, auth_user: UserResponse
) -> Optional[OrderResponse]:
    order = await order_repository.get_by_id(order_id)
    if order is None or order.user_id != auth_user.id:
        raise order_not_found_exception()
    if order.status != OrderStatus.TEMP:
        raise order_already_closed_exception()

    existing_line = await order_item_repository.get_one(order_id, item_id)
    if existing_line is None:
        raise order_item_not_found_exception()

    async with database.transaction():
        await order_item_repository.delete(order_id, item_id)
        remaining = await order_item_repository.count_for_order(order_id)
        if remaining == 0:
            await order_repository.delete_by_id(order_id)
            recommendation_service.invalidate_user_recommendations(auth_user.id)
            return None
        new_total = await order_repository.recalculate_total_price(order_id)
        await order_repository.update_total_price(order_id, new_total)

    recommendation_service.invalidate_user_recommendations(auth_user.id)
    return await _build_order_response(order_id)


async def purchase_order(order_id: int, auth_user: UserResponse) -> OrderResponse:
    order = await order_repository.get_by_id(order_id)
    if order is None or order.user_id != auth_user.id:
        raise order_not_found_exception()
    if order.status != OrderStatus.TEMP:
        raise order_already_closed_exception()

    items = await order_item_repository.get_items_for_order(order_id)
    if not items:
        raise empty_cart_exception()

    async with database.transaction():
        for line in items:
            rowcount = await item_repository.decrement_stock_atomic(
                line["item_id"], line["quantity"]
            )
            if rowcount == 0:
                # Re-fetch on failure to distinguish "out of stock" from
                # "insufficient stock"; the transaction rolls back on raise.
                current = await item_repository.get_item_by_id(line["item_id"])
                if current is None or current.stock == 0:
                    raise out_of_stock_exception(line["item_name"])
                raise insufficient_stock_exception(
                    line["item_name"], current.stock, line["quantity"]
                )
        # Lock prices into oi.price so the historical record preserves what
        # the user paid even if catalog prices change later.
        await order_item_repository.snapshot_prices_for_order(order_id)
        # Recompute against the freshly-snapshotted prices, then freeze the
        # order. Order matters: recalc before update_status so the CASE WHEN
        # still picks live prices (which now equal the snapshot).
        new_total = await order_repository.recalculate_total_price(order_id)
        await order_repository.update_total_price(order_id, new_total)
        await order_repository.update_status(order_id, OrderStatus.CLOSE)

    # Outside the transaction: Redis isn't part of MySQL's atomicity scope.
    item_repository.invalidate_all_cache()
    recommendation_service.invalidate_user_recommendations(auth_user.id)

    return await _build_order_response(order_id)


async def delete_order(order_id: int, auth_user: UserResponse):
    order = await order_repository.get_by_id(order_id)
    if order is None or order.user_id != auth_user.id:
        raise order_not_found_exception()

    async with database.transaction():
        await order_item_repository.delete_all_for_order(order_id)
        await order_repository.delete_by_id(order_id)

    recommendation_service.invalidate_user_recommendations(auth_user.id)
