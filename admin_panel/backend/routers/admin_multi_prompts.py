from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from admin_panel.backend.core.auth import admin_auth
from database import crud as db_crud
from database.models import MultiAnalysisPrompt

router = APIRouter(prefix="/admin/multi-prompts", tags=["Admin Multi Analysis Prompts"])


class MultiPromptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    prompt_text: str = Field(..., min_length=1)
    version: str = Field("1.0", min_length=1, max_length=20)
    description: Optional[str] = None
    make_active: bool = False


class MultiPromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    prompt_text: Optional[str] = Field(None, min_length=1)
    version: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None


class MultiPromptOut(BaseModel):
    id: int
    name: str
    prompt_text: str
    version: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[MultiPromptOut])
async def list_multi_prompts(_: str = Depends(admin_auth)):
    return await db_crud.admin_list_multi_analysis_prompts()


@router.post("", response_model=MultiPromptOut)
async def create_multi_prompt(data: MultiPromptBase, _: str = Depends(admin_auth)):
    return await db_crud.admin_create_multi_analysis_prompt(
        name=data.name,
        prompt_text=data.prompt_text,
        version=data.version,
        description=data.description,
        make_active=bool(data.make_active),
    )


@router.put("/{prompt_id}", response_model=MultiPromptOut)
async def update_multi_prompt(prompt_id: int, data: MultiPromptUpdate, _: str = Depends(admin_auth)):
    p = await db_crud.admin_update_multi_analysis_prompt(
        prompt_id=prompt_id,
        name=data.name,
        prompt_text=data.prompt_text,
        version=data.version,
        description=data.description,
    )
    if not p:
        raise HTTPException(status_code=404, detail="Multi-analysis prompt not found")
    return p


@router.post("/{prompt_id}/activate")
async def activate_multi_prompt(prompt_id: int, _: str = Depends(admin_auth)):
    ok = await db_crud.admin_activate_multi_analysis_prompt(prompt_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Multi-analysis prompt not found")
    return {"status": "activated"}


@router.delete("/{prompt_id}")
async def delete_multi_prompt(prompt_id: int, _: str = Depends(admin_auth)):
    ok = await db_crud.admin_delete_multi_analysis_prompt(prompt_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Multi-analysis prompt not found")
    return {"status": "deleted"}
