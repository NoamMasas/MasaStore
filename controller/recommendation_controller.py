from fastapi import APIRouter, Depends
from starlette import status

from model.recommendation_response import RecommendationResponse
from model.user_response import UserResponse
from service import auth_service, recommendation_service

router = APIRouter(
    prefix="/recommendation",
    tags=["recommendation"],
)


@router.get(
    "/",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recommendations(
    user: UserResponse = Depends(auth_service.validate_user),
):
    return await recommendation_service.get_recommendations(user)
