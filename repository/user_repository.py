from typing import Optional

from model.user import User
from model.user_request import UserRequest
from repository.database import database

TABLE_NAME = "user"


async def get_by_username(username: str) -> Optional[User]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE username=:username"
    result = await database.fetch_one(query, values={"username": username})
    if result:
        return User(**result)
    return None


async def get_by_id(user_id: int) -> Optional[User]:
    query = f"SELECT * FROM {TABLE_NAME} WHERE id=:user_id"
    result = await database.fetch_one(query, values={"user_id": user_id})
    if result:
        return User(**result)
    return None


async def create_user(user_request: UserRequest, hashed_password: str) -> int:
    query = f"""
        INSERT INTO {TABLE_NAME}
            (username, first_name, last_name, email, phone, country, city, hashed_password, is_active)
        VALUES
            (:username, :first_name, :last_name, :email, :phone, :country, :city, :hashed_password, :is_active)
    """
    values = {
        "username": user_request.username,
        "first_name": user_request.first_name,
        "last_name": user_request.last_name,
        "email": user_request.email,
        "phone": user_request.phone,
        "country": user_request.country,
        "city": user_request.city,
        "hashed_password": hashed_password,
        "is_active": True,
    }

    async with database.transaction():
        await database.execute(query, values)
        last_id_row = await database.fetch_one("SELECT LAST_INSERT_ID() AS id")
        return last_id_row["id"]


async def delete_by_id(user_id: int):
    delete_order_items_query = """
        DELETE oi FROM order_item oi
        INNER JOIN user_order uo ON oi.order_id = uo.id
        WHERE uo.user_id = :user_id
    """
    delete_favorites_query = "DELETE FROM user_favorite WHERE user_id = :user_id"
    delete_orders_query = "DELETE FROM user_order WHERE user_id = :user_id"
    delete_user_query = f"DELETE FROM {TABLE_NAME} WHERE id = :user_id"

    async with database.transaction():
        await database.execute(delete_order_items_query, values={"user_id": user_id})
        await database.execute(delete_favorites_query, values={"user_id": user_id})
        await database.execute(delete_orders_query, values={"user_id": user_id})
        await database.execute(delete_user_query, values={"user_id": user_id})
