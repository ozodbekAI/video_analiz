from __future__ import annotations

from datetime import datetime
import os
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from pathlib import Path

from admin_panel.backend.core.auth import admin_auth
from services.sample_report_service import SampleReportsService
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


def _to_out(payload: Dict[str, Any]) -> SampleOut:
    created = payload.get("created_at")
    created_at = created.isoformat() if hasattr(created, "isoformat") else (str(created) if created else None)
    return SampleOut(
        id=int(payload["id"]),
        report_name=str(payload.get("report_name") or ""),
        video_url=str(payload.get("video_url") or ""),
        video_type=str(payload.get("video_type") or "regular"),
        analysis_data=payload.get("analysis_data") or {},
        is_active=bool(payload.get("is_active")),
        created_at=created_at,
    )


@router.post("/upload", response_model=dict)
async def upload_sample(
    report_name: str = Form(..., min_length=1),
    video_url: str = Form(..., min_length=1),
    video_type: str = Form("regular"),  # regular | shorts
    pdf: UploadFile = File(...),
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

    # Save file
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

    new_id = await SampleReportsService.add_sample_report(
        report_name=report_name,
        video_url=video_url,
        analysis_data=analysis_data,
        video_type=video_type,
    )

    return {"id": new_id, "status": "created", "analysis_data": analysis_data}


@router.get("", response_model=List[SampleOut])
async def list_samples(
    video_type: Optional[str] = None,
    _: str = Depends(admin_auth),
):
    reports = await SampleReportsService.get_all_sample_reports(active_only=False)
    if video_type:
        reports = [r for r in reports if (r.get("video_type") == video_type)]
    return [_to_out(r) for r in reports]


@router.get("/{sample_id}", response_model=SampleOut)
async def get_sample(
    sample_id: int,
    _: str = Depends(admin_auth),
):
    r = await SampleReportsService.get_sample_report_by_id(sample_id)
    if not r:
        raise HTTPException(status_code=404, detail="Sample report not found")
    return _to_out(r)


@router.post("", response_model=dict)
async def create_sample(
    data: SampleCreate,
    _: str = Depends(admin_auth),
):
    if data.video_type not in ("regular", "shorts"):
        raise HTTPException(status_code=400, detail="video_type must be regular|shorts")

    new_id = await SampleReportsService.add_sample_report(
        report_name=data.report_name,
        video_url=data.video_url,
        analysis_data=data.analysis_data,
        video_type=data.video_type,
    )
    return {"id": new_id, "status": "created"}


@router.post("/{sample_id}/toggle")
async def toggle_sample(
    sample_id: int,
    _: str = Depends(admin_auth),
):
    r = await SampleReportsService.get_sample_report_by_id(sample_id)
    if not r:
        raise HTTPException(status_code=404, detail="Sample report not found")

    new_active = not bool(r.get("is_active"))
    ok = await SampleReportsService.update_sample_report(sample_id, is_active=new_active)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update sample")

    return {"status": "toggled", "is_active": new_active}


@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: int,
    _: str = Depends(admin_auth),
):
    ok = await SampleReportsService.delete_sample_report(sample_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Sample report not found")
    return {"status": "deleted"}
