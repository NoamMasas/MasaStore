from typing import List

from fastapi import APIRouter, Depends, Path
from starlette import status

from model.favorite_request import FavoriteRequest
from model.favorite_response import FavoriteResponse
from model.user_response import UserResponse
from service import auth_service, favorite_service

router = APIRouter(
    prefix="/favorite",
    tags=["favorite"],
)


@router.get(
    "/user/{user_id}",
    response_model=List[FavoriteResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_favorites(
    user: UserResponse = Depends(auth_service.validate_user),
    user_id: int = Path(gt=0),
):
    return await favorite_service.get_user_favorites(user_id, user)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    request: FavoriteRequest,
    user: UserResponse = Depends(auth_service.validate_user),
):
    await favorite_service.add_favorite(request, user)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    user: UserResponse = Depends(auth_service.validate_user),
    favorite_id: int = Path(gt=0),
):
    await favorite_service.delete_favorite(favorite_id, user)
