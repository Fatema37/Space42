"""Expected response shapes. Extra fields are ignored."""
from pydantic import BaseModel


class LoginResponse(BaseModel):
    id: int
    username: str
    email: str
    firstName: str
    lastName: str
    gender: str
    image: str
    accessToken: str
    refreshToken: str


class User(BaseModel):
    id: int
    username: str
    email: str
    firstName: str
    lastName: str
    role: str
