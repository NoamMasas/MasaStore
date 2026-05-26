from pydantic import BaseModel, condecimal


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    item_name: str
    price: condecimal(max_digits=10, decimal_places=2)
    stock: int
