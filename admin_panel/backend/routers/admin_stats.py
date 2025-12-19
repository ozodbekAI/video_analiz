from fastapi import APIRouter, Depends
from admin_panel.backend.core.auth import admin_auth
from database.crud import (
    get_total_users,
    get_total_videos,
    get_total_ai_requests,
    get_users_today,
    get_videos_today,
    get_ai_requests_today,
    get_analysis_type_stats,
    get_top_active_users,
    get_recent_videos,
)

router = APIRouter(prefix="/admin/stats", tags=["Admin Stats"])


@router.get("")
async def get_stats(_: str = Depends(admin_auth)):
    return {
        "total_users": await get_total_users(),
        "total_videos": await get_total_videos(),
        "total_requests": await get_total_ai_requests(),
        "users_today": await get_users_today(),
        "videos_today": await get_videos_today(),
        "requests_today": await get_ai_requests_today(),
        "analysis_types": await get_analysis_type_stats(),
    }


@router.get("/top-users")
async def top_users(limit: int = 10, _: str = Depends(admin_auth)):
    return await get_top_active_users(limit)


@router.get("/recent-videos")
async def recent_videos(limit: int = 10, _: str = Depends(admin_auth)):
    return await get_recent_videos(limit)
