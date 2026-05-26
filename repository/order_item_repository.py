from decimal import Decimal
from typing import List, Optional

from model.order_item import OrderItem
from repository.database import database

TABLE_NAME = "order_item"


async def get_items_for_order(order_id: int) -> List[dict]:
    # TEMP orders show the live catalog price (matches the MAIN page).
    # CLOSE orders show oi.price, the snapshot captured at purchase time.
    query = f"""
        SELECT
            oi.item_id,
            i.item_name,
            CASE WHEN uo.status = 'TEMP' THEN i.price ELSE oi.price END AS price,
            oi.quantity
        FROM {TABLE_NAME} oi
        INNER JOIN item i ON oi.item_id = i.id
        INNER JOIN user_order uo ON oi.order_id = uo.id
        WHERE oi.order_id = :order_id
        ORDER BY oi.item_id
    """
    results = await database.fetch_all(query, values={"order_id": order_id})
    return [dict(row) for row in results]


async def get_all_lines_for_user(user_id: int) -> List[dict]:
    query = f"""
        SELECT
            uo.id AS order_id,
            uo.status,
            uo.created_at,
            uo.total_price,
            oi.item_id,
            oi.quantity
        FROM {TABLE_NAME} oi
        INNER JOIN user_order uo ON oi.order_id = uo.id
        WHERE uo.user_id = :user_id
    """
    results = await database.fetch_all(query, values={"user_id": user_id})
    return [dict(row) for row in results]


async def get_one(order_id: int, item_id: int) -> Optional[OrderItem]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE order_id = :order_id AND item_id = :item_id"
    result = await database.fetch_one(query, values={"order_id": order_id, "item_id": item_id})
    if result:
        return OrderItem(**result)
    return None


async def add(order_id: int, item_id: int, quantity: int, price: Decimal):
    # `price` is captured as a placeholder; queries on TEMP orders use the
    # live catalog price. At purchase, snapshot_prices_for_order refreshes
    # this column with the moment-of-purchase price.
    query = f"""
        INSERT INTO {TABLE_NAME} (order_id, item_id, quantity, price)
        VALUES (:order_id, :item_id, :quantity, :price)
    """
    values = {
        "order_id": order_id,
        "item_id": item_id,
        "quantity": quantity,
        "price": price,
    }
    await database.execute(query, values)


async def snapshot_prices_for_order(order_id: int):
    # Locks oi.price = i.price for every line of the order. Called inside
    # purchase_order so the historical record captures what the user paid.
    query = f"""
        UPDATE {TABLE_NAME} oi
        INNER JOIN item i ON oi.item_id = i.id
        SET oi.price = i.price
        WHERE oi.order_id = :order_id
    """
    await database.execute(query, values={"order_id": order_id})


async def update_quantity(order_id: int, item_id: int, quantity: int):
    query = f"""
        UPDATE {TABLE_NAME}
        SET quantity = :quantity
        WHERE order_id = :order_id AND item_id = :item_id
    """
    values = {"order_id": order_id, "item_id": item_id, "quantity": quantity}
    await database.execute(query, values)


async def delete(order_id: int, item_id: int):
    query = f"DELETE FROM {TABLE_NAME} WHERE order_id = :order_id AND item_id = :item_id"
    await database.execute(query, values={"order_id": order_id, "item_id": item_id})


async def count_for_order(order_id: int) -> int:
    query = f"SELECT COUNT(*) AS cnt FROM {TABLE_NAME} WHERE order_id = :order_id"
    result = await database.fetch_one(query, values={"order_id": order_id})
    return result["cnt"]


async def delete_all_for_order(order_id: int):
    query = f"DELETE FROM {TABLE_NAME} WHERE order_id = :order_id"
    await database.execute(query, values={"order_id": order_id})
