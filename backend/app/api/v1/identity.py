"""Version 1 IAM endpoints for users, roles, and permissions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.database import get_db
from app.api.v1.schemas.identity import (
    PageMetadata,
    PermissionCreate,
    PermissionListResponse,
    PermissionRead,
    PermissionUpdate,
    RoleCreate,
    RoleListResponse,
    RolePermissionAssignment,
    RoleRead,
    RoleUpdate,
    UserCreate,
    UserListResponse,
    UserRead,
    UserRoleAssignment,
    UserUpdate,
)
from app.application.services.identity import PermissionService, RoleService, UserService
from app.infrastructure.persistence.audit import record_explicit_audit

router = APIRouter(tags=["identity-access-management"])
DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users.create"))],
)
def create_user(payload: UserCreate, db: DBSession):
    return UserService(db).create_user(**payload.model_dump())


@router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission("users.read"))],
)
def list_users(
    db: DBSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    service = UserService(db)
    return {
        "items": service.list_users(offset=offset, limit=limit),
        "page": PageMetadata(offset=offset, limit=limit, total=service.count_users()),
    }


@router.get(
    "/users/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users.read"))],
)
def get_user(user_id: uuid.UUID, db: DBSession):
    return UserService(db).get_user(user_id)


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users.update"))],
)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: DBSession):
    values = payload.model_dump(exclude_unset=True)
    if "email" in values and values["email"] is None:
        values["email"] = ""
    return UserService(db).update_user(user_id, **values)


@router.post(
    "/users/{user_id}/activate",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users.activate"))],
)
def activate_user(user_id: uuid.UUID, db: DBSession):
    return UserService(db).activate_user(user_id)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users.deactivate"))],
)
def deactivate_user(user_id: uuid.UUID, db: DBSession):
    return UserService(db).deactivate_user(user_id)


@router.get(
    "/users/{user_id}/roles",
    response_model=list[RoleRead],
    dependencies=[Depends(require_permission("users.read"))],
)
def list_user_roles(user_id: uuid.UUID, db: DBSession):
    return UserService(db).list_user_roles(user_id)


@router.post(
    "/users/{user_id}/roles",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users.roles.assign"))],
)
def assign_user_role(user_id: uuid.UUID, payload: UserRoleAssignment, db: DBSession):
    changed = UserService(db).assign_role(user_id, payload.role_id)
    if changed:
        record_explicit_audit(
            db,
            action="user.role_assigned",
            entity_type="user",
            entity_id=user_id,
            context_data={"role_id": str(payload.role_id)},
        )
    return {"changed": changed}


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users.roles.assign"))],
)
def remove_user_role(user_id: uuid.UUID, role_id: uuid.UUID, db: DBSession):
    changed = UserService(db).remove_role(user_id, role_id)
    if changed:
        record_explicit_audit(
            db,
            action="user.role_removed",
            entity_type="user",
            entity_id=user_id,
            context_data={"role_id": str(role_id)},
        )
    return {"changed": changed}


@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("roles.create"))],
)
def create_role(payload: RoleCreate, db: DBSession):
    return RoleService(db).create_role(**payload.model_dump())


@router.get(
    "/roles",
    response_model=RoleListResponse,
    dependencies=[Depends(require_permission("roles.read"))],
)
def list_roles(
    db: DBSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    service = RoleService(db)
    return {
        "items": service.list_roles(offset=offset, limit=limit),
        "page": PageMetadata(offset=offset, limit=limit, total=service.count_roles()),
    }


@router.get(
    "/roles/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles.read"))],
)
def get_role(role_id: uuid.UUID, db: DBSession):
    return RoleService(db).get_role(role_id)


@router.patch(
    "/roles/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles.update"))],
)
def update_role(role_id: uuid.UUID, payload: RoleUpdate, db: DBSession):
    values = payload.model_dump(exclude_unset=True)
    if "description" in values and values["description"] is None:
        values["description"] = ""
    return RoleService(db).update_role(role_id, **values)


@router.post(
    "/roles/{role_id}/activate",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles.activate"))],
)
def activate_role(role_id: uuid.UUID, db: DBSession):
    return RoleService(db).activate_role(role_id)


@router.post(
    "/roles/{role_id}/deactivate",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles.deactivate"))],
)
def deactivate_role(role_id: uuid.UUID, db: DBSession):
    return RoleService(db).deactivate_role(role_id)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("roles.delete"))],
)
def delete_role(role_id: uuid.UUID, db: DBSession):
    RoleService(db).delete_role(role_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/roles/{role_id}/permissions",
    response_model=list[PermissionRead],
    dependencies=[Depends(require_permission("roles.read"))],
)
def list_role_permissions(role_id: uuid.UUID, db: DBSession):
    return RoleService(db).list_role_permissions(role_id)


@router.post(
    "/roles/{role_id}/permissions",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("roles.permissions.assign"))],
)
def assign_role_permission(role_id: uuid.UUID, payload: RolePermissionAssignment, db: DBSession):
    changed = RoleService(db).assign_permission(role_id, payload.permission_id)
    if changed:
        record_explicit_audit(
            db,
            action="role.permission_assigned",
            entity_type="role",
            entity_id=role_id,
            context_data={"permission_id": str(payload.permission_id)},
        )
    return {"changed": changed}


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("roles.permissions.assign"))],
)
def remove_role_permission(role_id: uuid.UUID, permission_id: uuid.UUID, db: DBSession):
    changed = RoleService(db).remove_permission(role_id, permission_id)
    if changed:
        record_explicit_audit(
            db,
            action="role.permission_removed",
            entity_type="role",
            entity_id=role_id,
            context_data={"permission_id": str(permission_id)},
        )
    return {"changed": changed}


@router.post(
    "/permissions",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("permissions.create"))],
)
def create_permission(payload: PermissionCreate, db: DBSession):
    return PermissionService(db).create_permission(**payload.model_dump())


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
    dependencies=[Depends(require_permission("permissions.read"))],
)
def list_permissions(
    db: DBSession,
    module: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    service = PermissionService(db)
    return {
        "items": service.list_permissions(module=module, offset=offset, limit=limit),
        "page": PageMetadata(
            offset=offset,
            limit=limit,
            total=service.count_permissions(module=module),
        ),
    }


@router.get(
    "/permissions/{permission_id}",
    response_model=PermissionRead,
    dependencies=[Depends(require_permission("permissions.read"))],
)
def get_permission(permission_id: uuid.UUID, db: DBSession):
    return PermissionService(db).get_permission(permission_id)


@router.patch(
    "/permissions/{permission_id}",
    response_model=PermissionRead,
    dependencies=[Depends(require_permission("permissions.update"))],
)
def update_permission(permission_id: uuid.UUID, payload: PermissionUpdate, db: DBSession):
    values = payload.model_dump(exclude_unset=True)
    if "description" in values and values["description"] is None:
        values["description"] = ""
    return PermissionService(db).update_permission(permission_id, **values)


@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("permissions.delete"))],
)
def delete_permission(permission_id: uuid.UUID, db: DBSession):
    PermissionService(db).delete_permission(permission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
