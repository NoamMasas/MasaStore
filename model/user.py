from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    phone: str
    country: str
    city: str
    hashed_password: str
    is_active: bool
