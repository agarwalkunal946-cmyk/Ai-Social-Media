from pydantic import BaseModel


class UpdateModePayload(BaseModel):
    mode: str


class UpdateProfilePayload(BaseModel):
    display_name: str


class AdminUpdateUserPayload(BaseModel):
    display_name: str | None = None
    mode: str | None = None
    status: str | None = None
