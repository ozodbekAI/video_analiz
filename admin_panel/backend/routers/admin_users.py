from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from admin_panel.backend.core.auth import admin_auth
from database.engine import get_session
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
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    """Admin UI currently expects a simple list.

    - Supports basic search by username or user_id substring.
    - Supports pagination via page/limit (still returns a list to avoid breaking UI).
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    if limit > 200:
        limit = 200

    q = select(User)
    if search:
        # "contains" search; keeps it simple and DB-agnostic.
        like = f"%{search.lower()}%"
        q = q.where(
            (User.username.ilike(like)) | (cast(User.user_id, String).ilike(like))
        )

    q = q.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(User).where(User.user_id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.put("/{user_id}/limit")
async def update_user_limit(
    user_id: int,
    payload: LimitUpdate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(User).where(User.user_id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    u.analyses_limit = payload.limit
    await db.commit()
    return {"status": "updated"}


@router.post("/{user_id}/reset")
async def reset_user_usage(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(User).where(User.user_id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    u.analyses_used = 0
    u.last_reset_date = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"status": "reset"}


@router.put("/{user_id}/tariff")
async def update_user_tariff(
    user_id: int,
    payload: TariffUpdate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(User).where(User.user_id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    u.tariff_plan = payload.tariff
    await db.commit()
    return {"status": "updated"}
