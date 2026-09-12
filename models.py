"""Pydantic response models — the schema oracle for contract tests.
Extra fields are ignored, so a new field in the sandbox doesn't break the suite."""
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
