from datetime import datetime
from typing import List

from pydantic import BaseModel, condecimal

from model.order_status import OrderStatus


class OrderItemDetail(BaseModel):
    item_id: int
    item_name: str
    price: condecimal(max_digits=10, decimal_places=2)
    quantity: int


class OrderResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    shipping_address: str
    total_price: condecimal(max_digits=10, decimal_places=2)
    status: OrderStatus
    items: List[OrderItemDetail]
