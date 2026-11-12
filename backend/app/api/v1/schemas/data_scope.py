"""API contracts for user data-scope grants."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DataScopeGrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope_type: Literal["global", "company", "department", "owner"]
    scope_value: str = Field(min_length=1, max_length=160)

    @field_validator("scope_value")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        return value.strip()


class DataScopeGrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    scope_type: str
    scope_value: str
