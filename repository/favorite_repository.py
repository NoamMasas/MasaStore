from typing import List, Optional

from model.favorite import Favorite
from repository.database import database

TABLE_NAME = "user_favorite"


async def get_favorites_by_user(user_id: int) -> List[dict]:
    query = f"""
        SELECT
            f.id,
            f.user_id,
            f.item_id,
            i.item_name,
            i.price,
            i.stock
        FROM {TABLE_NAME} f
        INNER JOIN item i ON f.item_id = i.id
        WHERE f.user_id = :user_id
    """
    results = await database.fetch_all(query, values={"user_id": user_id})
    return [dict(row) for row in results]


async def get_by_id(favorite_id: int) -> Optional[Favorite]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE id = :favorite_id"
    result = await database.fetch_one(query, values={"favorite_id": favorite_id})
    if result:
        return Favorite(**result)
    return None


async def get_by_user_and_item(user_id: int, item_id: int) -> Optional[Favorite]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE user_id = :user_id AND item_id = :item_id"
    result = await database.fetch_one(query, values={"user_id": user_id, "item_id": item_id})
    if result:
        return Favorite(**result)
    return None


async def create(user_id: int, item_id: int) -> int:
    query = f"""
        INSERT INTO {TABLE_NAME} (user_id, item_id)
        VALUES (:user_id, :item_id)
    """
    values = {"user_id": user_id, "item_id": item_id}

    async with database.transaction():
        await database.execute(query, values)
        last_id_row = await database.fetch_one("SELECT LAST_INSERT_ID() AS id")
        return last_id_row["id"]


async def delete_by_id(favorite_id: int):
    query = f"DELETE FROM {TABLE_NAME} WHERE id = :favorite_id"
    await database.execute(query, values={"favorite_id": favorite_id})
