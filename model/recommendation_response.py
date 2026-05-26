from typing import List

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    item_id: int
    item_name: str
    category: str
    price: float
    probability: float


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[RecommendationItem]
    model_version: str
    trained_at: str
