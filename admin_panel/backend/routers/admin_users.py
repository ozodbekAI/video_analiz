from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from admin_panel.backend.core.auth import admin_auth
from database import crud as db_crud
from database.models import User

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


class UserOut(BaseModel):
    user_id: int
    username: Optional[str] = None
    tariff_plan: Optional[str] = None
    analyses_limit: int
    analyses_used: int
    verification_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LimitUpdate(BaseModel):
    limit: int = Field(..., ge=0)


class TariffUpdate(BaseModel):
    tariff: str = Field(..., min_length=1)


@router.get("", response_model=List[UserOut])
async def list_users(
    search: str = "",
    page: int = 1,
    limit: int = 20,
    _: str = Depends(admin_auth),
):
    return await db_crud.admin_list_users(search=search, page=page, limit=limit)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    _: str = Depends(admin_auth),
):
    u = await db_crud.admin_get_user(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.put("/{user_id}/limit")
async def update_user_limit(
    user_id: int,
    payload: LimitUpdate,
    _: str = Depends(admin_auth),
):
    u = await db_crud.admin_get_user(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    await db_crud.admin_set_user_limit(user_id, payload.limit)
    return {"status": "updated"}


@router.post("/{user_id}/reset")
async def reset_user_usage(
    user_id: int,
    _: str = Depends(admin_auth),
):
    u = await db_crud.admin_get_user(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    await db_crud.admin_reset_user_usage(user_id)
    return {"status": "reset"}


@router.put("/{user_id}/tariff")
async def update_user_tariff(
    user_id: int,
    payload: TariffUpdate,
    _: str = Depends(admin_auth),
):
    u = await db_crud.admin_get_user(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    ok = await db_crud.admin_set_user_tariff(user_id, payload.tariff)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update tariff")
    return {"status": "updated"}
