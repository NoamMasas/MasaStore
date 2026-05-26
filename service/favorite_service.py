from typing import List

from exceptions.exception import (
    favorite_already_exists_exception,
    favorite_not_found_exception,
    item_not_found_exception,
    not_authorized_exception,
)
from model.favorite_request import FavoriteRequest
from model.favorite_response import FavoriteResponse
from model.user_response import UserResponse
from repository import favorite_repository, item_repository
from service import recommendation_service


async def get_user_favorites(user_id: int, auth_user: UserResponse) -> List[FavoriteResponse]:
    if auth_user.id != user_id:
        raise not_authorized_exception()
    rows = await favorite_repository.get_favorites_by_user(user_id)
    return [FavoriteResponse(**row) for row in rows]


async def add_favorite(request: FavoriteRequest, auth_user: UserResponse) -> int:
    item = await item_repository.get_item_by_id(request.item_id)
    if item is None:
        raise item_not_found_exception()

    existing = await favorite_repository.get_by_user_and_item(auth_user.id, request.item_id)
    if existing is not None:
        raise favorite_already_exists_exception()

    new_id = await favorite_repository.create(auth_user.id, request.item_id)
    recommendation_service.invalidate_user_recommendations(auth_user.id)
    return new_id


async def delete_favorite(favorite_id: int, auth_user: UserResponse):
    favorite = await favorite_repository.get_by_id(favorite_id)
    # Mask "not yours" as "not found" to avoid leaking other users' ids.
    if favorite is None or favorite.user_id != auth_user.id:
        raise favorite_not_found_exception()
    await favorite_repository.delete_by_id(favorite_id)
    recommendation_service.invalidate_user_recommendations(auth_user.id)
