from pydantic import BaseModel


class FavoriteRequest(BaseModel):
    item_id: int
