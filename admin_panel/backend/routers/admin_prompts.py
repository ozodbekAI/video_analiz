from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from admin_panel.backend.core.auth import admin_auth
from database import crud as db_crud
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


def _normalize_prompt(p: Prompt) -> Prompt:
    # ResponseValidationError bo'lmasligi uchun
    if p.order is None:
        p.order = 0
    if p.category is None:
        p.category = "my"
    if p.analysis_type is None:
        p.analysis_type = "simple"
    return p


@router.get("/", response_model=List[PromptOut])
async def list_prompts(
    category: Optional[str] = None,
    analysis_type: Optional[str] = None,
    _: str = Depends(admin_auth),
):
    items = await db_crud.admin_list_prompts(category=category, analysis_type=analysis_type)
    return [_normalize_prompt(p) for p in items]


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: int,
    _: str = Depends(admin_auth),
):
    prompt = await db_crud.admin_get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _normalize_prompt(prompt)


@router.post("/", response_model=PromptOut)
async def add_prompt(
    data: PromptBase,
    _: str = Depends(admin_auth),
):
    prompt = await db_crud.admin_create_prompt(
        name=data.name,
        prompt_text=data.prompt_text,
        category=data.category,
        analysis_type=data.analysis_type,
        module_id=data.module_id,
    )
    return _normalize_prompt(prompt)


@router.put("/{prompt_id}", response_model=PromptOut)
async def edit_prompt(
    prompt_id: int,
    data: PromptBase,
    _: str = Depends(admin_auth),
):
    prompt = await db_crud.admin_update_prompt(
        prompt_id=prompt_id,
        name=data.name,
        prompt_text=data.prompt_text,
        category=data.category,
        analysis_type=data.analysis_type,
        module_id=data.module_id,
    )
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _normalize_prompt(prompt)


@router.delete("/{prompt_id}")
async def remove_prompt(
    prompt_id: int,
    _: str = Depends(admin_auth),
):
    ok = await db_crud.admin_delete_prompt(prompt_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"status": "deleted"}


@router.post("/reorder")
async def reorder_prompts(
    data: PromptReorder,
    _: str = Depends(admin_auth),
):
    try:
        await db_crud.admin_reorder_prompts([x.model_dump() for x in data.orders])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "reordered"}
