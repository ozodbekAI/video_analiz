from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from admin_panel.backend.core.auth import admin_auth


router = APIRouter(prefix="/admin", tags=["Admin Upload"])


UPLOAD_ROOT = Path(os.getenv("ADMIN_UPLOAD_DIR", "./uploads")).resolve()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form("prompt"),
    _: str = Depends(admin_auth),
):
    """Generic file upload endpoint used by the Admin UI.

    Current UI mostly reads .txt client-side, but keeping the endpoint prevents future breakage.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    safe_type = "".join(ch for ch in type if ch.isalnum() or ch in ("-", "_")) or "misc"
    folder = (UPLOAD_ROOT / safe_type)
    folder.mkdir(parents=True, exist_ok=True)

    # Avoid path traversal
    safe_name = Path(file.filename).name
    dest = folder / safe_name

    content = await file.read()
    dest.write_bytes(content)

    return {
        "status": "uploaded",
        "filename": safe_name,
        "type": safe_type,
        "path": str(dest),
        "size": len(content),
    }
