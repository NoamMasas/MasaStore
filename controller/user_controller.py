from fastapi import APIRouter, Depends, Path
from starlette import status

from exceptions.exception import not_authorized_exception
from model.user_request import UserRequest
from model.user_response import UserResponse
from service import auth_service, user_service

router = APIRouter(
    prefix="/user",
    tags=["user"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user_request: UserRequest):
    await user_service.create_user(user_request)


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user_by_id(
    user: UserResponse = Depends(auth_service.validate_user),
    user_id: int = Path(gt=0),
):
    return await user_service.get_user_by_id(user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user: UserResponse = Depends(auth_service.validate_user),
    user_id: int = Path(gt=0),
):
    if user.id != user_id:
        raise not_authorized_exception()
    await user_service.delete_user(user_id)
