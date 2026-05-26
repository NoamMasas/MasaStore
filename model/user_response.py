from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    phone: str
    country: str
    city: str
