from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from admin_panel.backend.core.auth import admin_auth
from database.engine import get_session, get_session
from database.models import Prompt


router = APIRouter(prefix="/admin/prompts", tags=["Admin Prompts"])


class PromptBase(BaseModel):
    name: str = Field(..., min_length=1)
    prompt_text: str = Field(..., min_length=1)
    category: str = "my"
    analysis_type: str = "simple"
    module_id: Optional[str] = None


class PromptOut(PromptBase):
    id: int
    order: int = 0

    class Config:
        from_attributes = True


class PromptReorderItem(BaseModel):
    id: int
    order: int


class PromptReorder(BaseModel):
    orders: List[PromptReorderItem]


@router.get("/", response_model=List[PromptOut])
async def list_prompts(
    category: Optional[str] = None,
    analysis_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    q = select(Prompt)
    if category:
        q = q.where(Prompt.category == category)
    if analysis_type:
        q = q.where(Prompt.analysis_type == analysis_type)
    res = await db.execute(q.order_by(Prompt.order))
    return res.scalars().all()


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = res.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("/", response_model=PromptOut)
async def add_prompt(
    data: PromptBase,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    # Put new prompts at the end of the current category/type ordering
    max_order_res = await db.execute(
        select(Prompt.order)
        .where(Prompt.category == data.category)
        .where(Prompt.analysis_type == data.analysis_type)
        .order_by(Prompt.order.desc())
        .limit(1)
    )
    max_order = max_order_res.scalar_one_or_none()
    next_order = (max_order + 1) if max_order is not None else 0

    prompt = Prompt(
        name=data.name,
        prompt_text=data.prompt_text,
        analysis_type=data.analysis_type,
        category=data.category,
        module_id=data.module_id,
        order=next_order,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.put("/{prompt_id}", response_model=PromptOut)
async def edit_prompt(
    prompt_id: int,
    data: PromptBase,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = res.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.name = data.name
    prompt.prompt_text = data.prompt_text
    prompt.category = data.category
    prompt.analysis_type = data.analysis_type
    prompt.module_id = data.module_id

    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}")
async def remove_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = res.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await db.delete(prompt)
    await db.commit()
    return {"status": "deleted"}


@router.post("/reorder")
async def reorder_prompts(
    data: PromptReorder,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    # Minimal validation: ensure all IDs exist
    ids = [x.id for x in data.orders]
    existing = await db.execute(select(Prompt.id).where(Prompt.id.in_(ids)))
    existing_ids = set(existing.scalars().all())
    missing = [pid for pid in ids if pid not in existing_ids]
    if missing:
        raise HTTPException(status_code=400, detail={"missing_prompt_ids": missing})

    # Apply updates
    for item in data.orders:
        res = await db.execute(select(Prompt).where(Prompt.id == item.id))
        p = res.scalar_one()
        p.order = item.order
    await db.commit()
    return {"status": "reordered"}
