"""Authentication and authorization utilities"""
from fastapi import HTTPException
from typing import Optional
from app.core.enums import UserRole


async def verify_resource_owner(
    resource_creator_id: int,
    current_user,
    resource_name: str = "Resource"
) -> None:

    if current_user.role == UserRole.AGENT and resource_creator_id != int(current_user.id):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: You can only access your own {resource_name}s"
        )


def filter_by_user(query, model, current_user):

    if current_user.role == UserRole.AGENT:
        return query.where(model.created_by == int(current_user.id))
    return query


def check_ownership(item, current_user, resource_name: str = "Resource") -> None:

    if current_user.role == UserRole.AGENT and item.created_by != int(current_user.id):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: You can only access your own {resource_name}s"
        )


def check_not_found(item, resource_name: str = "Resource", resource_id: Optional[int] = None) -> None:

    if not item:
        if resource_id:
            raise HTTPException(
                status_code=404,
                detail=f"{resource_name} with id {resource_id} not found"
            )
        raise HTTPException(status_code=404, detail=f"{resource_name} not found")
