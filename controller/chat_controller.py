from fastapi import APIRouter, Depends
from starlette import status

from model.chat_request import ChatRequest
from model.chat_response import ChatResponse
from model.user_response import UserResponse
from service import auth_service, chat_service

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def send_chat(
    request: ChatRequest,
    user: UserResponse = Depends(auth_service.validate_user),
):
    return await chat_service.send_chat(request, user)


@router.post("/reset/", status_code=status.HTTP_200_OK)
async def reset_chat(
    user: UserResponse = Depends(auth_service.validate_user),
):
    await chat_service.reset_chat(user)
    return {"message": "Counter reset"}
