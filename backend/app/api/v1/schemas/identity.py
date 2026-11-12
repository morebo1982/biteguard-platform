"""Request and response schemas for IAM identity resources.

These schemas define API contracts only; they do not expose endpoints or
perform persistence, authorization, or transaction management.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Username = Annotated[str, Field(min_length=1, max_length=80)]
DisplayName = Annotated[str, Field(min_length=1, max_length=160)]
RoleCode = Annotated[str, Field(min_length=1, max_length=80)]
PermissionCode = Annotated[str, Field(min_length=1, max_length=120)]
ShortName = Annotated[str, Field(min_length=1, max_length=160)]
Description = Annotated[str | None, Field(max_length=500)]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ORMReadModel(APIModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UserCreate(APIModel):
    username: Username
    display_name: DisplayName
    email: Annotated[str | None, Field(max_length=254)] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required.")
        return value


class UserUpdate(APIModel):
    username: Username | None = None
    display_name: DisplayName | None = None
    email: Annotated[str | None, Field(max_length=254)] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required.")
        return value


class UserRead(ORMReadModel):
    id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleCreate(APIModel):
    code: RoleCode
    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Description = None


class RoleUpdate(APIModel):
    code: RoleCode | None = None
    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    description: Description = None


class RoleRead(ORMReadModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PermissionCreate(APIModel):
    code: PermissionCode
    name: ShortName
    module: Annotated[str, Field(min_length=1, max_length=80)]
    description: Description = None


class PermissionUpdate(APIModel):
    code: PermissionCode | None = None
    name: ShortName | None = None
    module: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    description: Description = None


class PermissionRead(ORMReadModel):
    id: uuid.UUID
    code: str
    name: str
    module: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class PageMetadata(APIModel):
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    total: int = Field(ge=0)


class UserListResponse(APIModel):
    items: list[UserRead]
    page: PageMetadata


class RoleListResponse(APIModel):
    items: list[RoleRead]
    page: PageMetadata


class PermissionListResponse(APIModel):
    items: list[PermissionRead]
    page: PageMetadata


class UserRoleAssignment(APIModel):
    role_id: uuid.UUID


class RolePermissionAssignment(APIModel):
    permission_id: uuid.UUID
