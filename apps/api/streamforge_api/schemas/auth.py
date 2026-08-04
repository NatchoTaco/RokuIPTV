from pydantic import BaseModel, ConfigDict, EmailStr, Field

from streamforge_api.schemas.setup import SetupStateResponse


class BootstrapAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=160)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    user: UserPublic
    setup: SetupStateResponse
