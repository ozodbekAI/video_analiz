from __future__ import annotations

import datetime
import json
import os
from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from fastapi.params import Form
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional

from admin_panel.backend.core.auth import admin_auth
from database.engine import get_session
from database.models import SampleReport
from services.youtube_service import extract_video_id


router = APIRouter(prefix="/admin/samples", tags=["Admin Samples"])


class SampleCreate(BaseModel):
    report_name: str = Field(..., min_length=1)
    video_url: str = Field(..., min_length=1)
    video_type: str = "regular"  # regular | shorts
    analysis_data: Dict[str, Any] = Field(default_factory=dict)


class SampleOut(BaseModel):
    id: int
    report_name: str
    video_url: str
    video_type: str
    analysis_data: Dict[str, Any]
    is_active: bool
    created_at: Optional[str] = None



@router.post("/upload", response_model=dict)
async def upload_sample(
    report_name: str = Form(..., min_length=1),
    video_url: str = Form(..., min_length=1),
    video_type: str = Form("regular"),  # regular | shorts
    pdf: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    if video_type not in ("regular", "shorts"):
        raise HTTPException(status_code=400, detail="video_type must be regular|shorts")

    if not pdf:
        raise HTTPException(status_code=400, detail="pdf file required")

    if pdf.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="File must be PDF")

    video_id = extract_video_id(video_url) or "unknown"
    demo_dir = Path("reports/demo")
    demo_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_video_id = "".join([c for c in video_id if c.isalnum() or c in ("_", "-")])[:32]
    filename = f"demo_{safe_video_id}_{ts}.pdf"
    pdf_path = demo_dir / filename

    # Faylni diskka saqlash
    try:
        content = await pdf.read()
        with open(pdf_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {str(e)}")

    file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else None

    analysis_data = {
        "pdf_path": str(pdf_path),
        "video_id": video_id,
        "file_size": file_size,
        "uploaded_at": datetime.now().isoformat(),
        "original_filename": pdf.filename,
    }

    r = SampleReport(
        report_name=report_name,
        video_url=video_url,
        video_type=video_type,
        analysis_data=json.dumps(analysis_data, ensure_ascii=False),
        is_active=True,
    )

    db.add(r)
    await db.commit()
    await db.refresh(r)

    return {"id": r.id, "status": "created", "analysis_data": analysis_data}


@router.get("", response_model=List[SampleOut])
async def list_samples(
    video_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    q = select(SampleReport)
    if video_type:
        q = q.where(SampleReport.video_type == video_type)
    q = q.order_by(SampleReport.created_at.desc())
    res = await db.execute(q)
    reports = res.scalars().all()
    out: List[SampleOut] = []
    for r in reports:
        try:
            payload = json.loads(r.analysis_data) if r.analysis_data else {}
        except Exception:
            payload = {"_raw": r.analysis_data}
        out.append(
            SampleOut(
                id=r.id,
                report_name=r.report_name,
                video_url=r.video_url,
                video_type=r.video_type,
                analysis_data=payload,
                is_active=r.is_active,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )
    return out


@router.get("/{sample_id}", response_model=SampleOut)
async def get_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(SampleReport).where(SampleReport.id == sample_id))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Sample report not found")

    try:
        payload = json.loads(r.analysis_data) if r.analysis_data else {}
    except Exception:
        payload = {"_raw": r.analysis_data}

    return SampleOut(
        id=r.id,
        report_name=r.report_name,
        video_url=r.video_url,
        video_type=r.video_type,
        analysis_data=payload,
        is_active=r.is_active,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


@router.post("", response_model=dict)
async def create_sample(
    data: SampleCreate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    r = SampleReport(
        report_name=data.report_name,
        video_url=data.video_url,
        video_type=data.video_type,
        analysis_data=json.dumps(data.analysis_data, ensure_ascii=False),
        is_active=True,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": r.id, "status": "created"}


@router.post("/{sample_id}/toggle")
async def toggle_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(SampleReport).where(SampleReport.id == sample_id))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Sample report not found")
    r.is_active = not r.is_active
    await db.commit()
    return {"status": "toggled", "is_active": r.is_active}


@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(admin_auth),
):
    res = await db.execute(select(SampleReport).where(SampleReport.id == sample_id))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Sample report not found")
    await db.delete(r)
    await db.commit()
    return {"status": "deleted"}
