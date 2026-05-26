import json
from typing import List, Optional

from model.item import Item
from repository import cache_repository
from repository.database import database

TABLE_NAME = "item"
CACHE_KEY_ALL = "items:all"

_OPERATORS = {"lt": "<", "gt": ">", "eq": "="}


async def get_all_items() -> List[Item]:
    if cache_repository.is_key_exists(CACHE_KEY_ALL):
        cached = cache_repository.get_cache_entity(CACHE_KEY_ALL)
        return [Item(**row) for row in json.loads(cached)]

    query = f"SELECT * FROM {TABLE_NAME}"
    results = await database.fetch_all(query)
    items = [Item(**row) for row in results]

    cache_repository.create_cache_entity(
        CACHE_KEY_ALL,
        json.dumps([item.dict() for item in items], default=str),
    )
    return items


async def get_item_by_id(item_id: int) -> Optional[Item]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE id=:item_id"
    result = await database.fetch_one(query, values={"item_id": item_id})
    if result:
        return Item(**result)
    return None


async def search_items(
    name: Optional[str],
    stock_op: Optional[str],
    stock_value: Optional[int],
    price_op: Optional[str],
    price_value: Optional[float],
) -> List[Item]:
    where_clauses: List[str] = []
    values: dict = {}

    if name:
        parts = [p.strip() for p in name.split(",") if p.strip()]
        if parts:
            or_clauses = []
            for i, part in enumerate(parts):
                param = f"name_{i}"
                or_clauses.append(f"item_name LIKE :{param}")
                values[param] = f"%{part}%"
            where_clauses.append("(" + " OR ".join(or_clauses) + ")")

    if stock_op and stock_value is not None:
        where_clauses.append(f"stock {_OPERATORS[stock_op]} :stock_value")
        values["stock_value"] = stock_value

    if price_op and price_value is not None:
        where_clauses.append(f"price {_OPERATORS[price_op]} :price_value")
        values["price_value"] = price_value

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    query = f"SELECT * FROM {TABLE_NAME} WHERE {where_sql}"
    results = await database.fetch_all(query, values=values)
    return [Item(**row) for row in results]


def invalidate_all_cache():
    cache_repository.remove_cache_entity(CACHE_KEY_ALL)


async def decrement_stock_atomic(item_id: int, quantity: int) -> int:
    """
    Returns 1 if the decrement succeeded, 0 if stock was insufficient
    (the WHERE clause blocked the UPDATE).

    MUST be called inside database.transaction() — callers rely on rollback
    when one of several sibling decrements fails.

    WARNING: `quantity` is order_item.quantity (units being bought). Never
    pass item.stock here — `stock - stock` would zero inventory.
    """
    query = """
        UPDATE item
        SET stock = stock - :quantity
        WHERE id = :item_id AND stock >= :quantity
    """
    return await database.execute(
        query, values={"item_id": item_id, "quantity": quantity}
    )
