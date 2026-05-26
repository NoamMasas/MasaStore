from typing import Literal

from pydantic import BaseModel, Field

# Adding codes here requires retraining the recommender — unknown codes
# give an all-zero country one-hot, silently weakening predictions.
SUPPORTED_COUNTRIES: dict = {
    "IL": "Israel",
    "US": "United States",
    "UK": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "ES": "Spain",
    "IT": "Italy",
    "JP": "Japan",
    "BR": "Brazil",
    "IN": "India",
}


class UserRequest(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: str
    phone: str
    country: Literal["IL", "US", "UK", "DE", "FR", "ES", "IT", "JP", "BR", "IN"]
    city: str
    password: str = Field(..., min_length=6)
