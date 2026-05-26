from pydantic import BaseModel


class OrderItemAddRequest(BaseModel):
    item_id: int
    quantity: int = 1
