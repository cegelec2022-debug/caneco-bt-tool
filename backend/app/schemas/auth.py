from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str
    full_name: str
    role: str = "BE"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
