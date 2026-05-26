from pydantic import BaseModel


class AuthResponse(BaseModel):
    jwt_token: str
    access_token: str
    token_type: str = "bearer"
