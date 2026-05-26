from pydantic import BaseModel, condecimal


class OrderItem(BaseModel):
    order_id: int
    item_id: int
    quantity: int
    price: condecimal(max_digits=10, decimal_places=2)
