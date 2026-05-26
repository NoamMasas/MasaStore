from typing import Optional

from passlib.context import CryptContext

from model.user import User
from model.user_request import UserRequest
from model.user_response import UserResponse
from exceptions.exception import username_taken_exception, user_not_found_exception
from repository import user_repository

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return bcrypt_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


async def create_user(user_request: UserRequest) -> int:
    if not await validate_unique_username(user_request.username):
        raise username_taken_exception()
    hashed_password = get_password_hash(user_request.password)
    return await user_repository.create_user(user_request, hashed_password)


async def get_user_by_id(user_id: int) -> UserResponse:
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise user_not_found_exception()
    return UserResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        country=user.country,
        city=user.city,
    )


async def get_user_by_username(username: str) -> Optional[User]:
    return await user_repository.get_by_username(username)


async def validate_unique_username(username: str) -> bool:
    existing_user = await user_repository.get_by_username(username)
    return existing_user is None


async def delete_user(user_id: int):
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise user_not_found_exception()
    await user_repository.delete_by_id(user_id)
