from datetime import datetime
from typing import Optional

from pydantic import BaseModel, condecimal

from model.order_status import OrderStatus


class Order(BaseModel):
    id: Optional[int] = None
    user_id: int
    created_at: Optional[datetime] = None
    shipping_address: str
    total_price: condecimal(max_digits=10, decimal_places=2) = 0
    status: OrderStatus = OrderStatus.TEMP
