from decimal import Decimal
from typing import List, Optional

from model.order import Order
from model.order_status import OrderStatus
from repository.database import database

TABLE_NAME = "user_order"


async def get_orders_by_user(user_id: int) -> List[Order]:
    query = f"""
        SELECT * FROM {TABLE_NAME}
        WHERE user_id = :user_id
        ORDER BY FIELD(status, 'TEMP', 'CLOSE'), created_at DESC
    """
    results = await database.fetch_all(query, values={"user_id": user_id})
    return [Order(**row) for row in results]


async def get_by_id(order_id: int) -> Optional[Order]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE id = :order_id"
    result = await database.fetch_one(query, values={"order_id": order_id})
    if result:
        return Order(**result)
    return None


async def get_temp_order_by_user(user_id: int) -> Optional[Order]:
    query = f"""
        SELECT * FROM {TABLE_NAME}
        WHERE user_id = :user_id AND status = 'TEMP'
        LIMIT 1
    """
    result = await database.fetch_one(query, values={"user_id": user_id})
    if result:
        return Order(**result)
    return None


async def create(user_id: int, shipping_address: str) -> int:
    query = f"""
        INSERT INTO {TABLE_NAME} (user_id, shipping_address)
        VALUES (:user_id, :shipping_address)
    """
    values = {"user_id": user_id, "shipping_address": shipping_address}

    async with database.transaction():
        await database.execute(query, values)
        last_id_row = await database.fetch_one("SELECT LAST_INSERT_ID() AS id")
        return last_id_row["id"]


async def update_total_price(order_id: int, total_price: Decimal):
    query = f"UPDATE {TABLE_NAME} SET total_price = :total_price WHERE id = :order_id"
    await database.execute(query, values={"total_price": total_price, "order_id": order_id})


async def update_status(order_id: int, status: OrderStatus):
    query = f"UPDATE {TABLE_NAME} SET status = :status WHERE id = :order_id"
    await database.execute(query, values={"status": status.name, "order_id": order_id})


async def recalculate_total_price(order_id: int) -> Decimal:
    # TEMP totals follow the live catalog price; CLOSE totals use the
    # snapshot captured at purchase. Matches get_items_for_order.
    query = """
        SELECT COALESCE(SUM(
            CASE WHEN uo.status = 'TEMP' THEN i.price ELSE oi.price END
            * oi.quantity
        ), 0) AS total
        FROM order_item oi
        INNER JOIN item i ON oi.item_id = i.id
        INNER JOIN user_order uo ON oi.order_id = uo.id
        WHERE oi.order_id = :order_id
    """
    result = await database.fetch_one(query, values={"order_id": order_id})
    return Decimal(str(result["total"]))


async def delete_by_id(order_id: int):
    query = f"DELETE FROM {TABLE_NAME} WHERE id = :order_id"
    await database.execute(query, values={"order_id": order_id})
