import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select

from database.engine import async_session
from database.models import VideoCommentsCache

# Where cached payloads are stored (persistent)
CACHE_DIR = Path("cache") / "comments"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default TTL requested by user
DEFAULT_TTL_HOURS = 72


@dataclass
class CacheInfo:
    hit: bool
    fetched_at: datetime


def _cache_file_path(video_id: str) -> str:
    # One file per YouTube video id
    return str(CACHE_DIR / f"{video_id}.json")


def _safe_read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        if not path or not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _safe_write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


async def _get_cache_row(video_id: str) -> Optional[VideoCommentsCache]:
    async with async_session() as session:
        res = await session.execute(
            select(VideoCommentsCache).where(VideoCommentsCache.youtube_video_id == video_id)
        )
        return res.scalar_one_or_none()


async def _upsert_cache_row(video_id: str, file_path: str, fetched_at: datetime) -> None:
    async with async_session() as session:
        res = await session.execute(
            select(VideoCommentsCache).where(VideoCommentsCache.youtube_video_id == video_id)
        )
        row = res.scalar_one_or_none()

        if row:
            row.file_path = file_path
            row.fetched_at = fetched_at
            row.updated_at = fetched_at
        else:
            row = VideoCommentsCache(
                youtube_video_id=video_id,
                file_path=file_path,
                fetched_at=fetched_at,
                updated_at=fetched_at,
            )
            session.add(row)

        await session.commit()


async def get_video_comments_with_metrics_cached(
    video_id: str,
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> Dict[str, Any]:
    """Return comments+metadata+metrics for a video using persistent cache.

    Behavior:
    - If cached record exists AND cache age <= ttl_hours AND file exists -> load from file.
    - Otherwise fetch from YouTube, overwrite cache file + DB row.
    """
    now = datetime.now(tz=timezone.utc)

    # 1) Try cache
    row = await _get_cache_row(video_id)
    if row and row.fetched_at:
        age = now - row.fetched_at
        if age <= timedelta(hours=ttl_hours):
            payload = _safe_read_json(row.file_path)
            if payload:
                payload.setdefault("_cache", {})
                payload["_cache"].update(
                    {
                        "hit": True,
                        "fetched_at": row.fetched_at.isoformat(),
                        "age_hours": round(age.total_seconds() / 3600, 2),
                    }
                )
                return payload

    # 2) Cache miss / stale -> fetch
    from services.youtube_service import get_video_comments_with_metrics

    # googleapiclient is sync; run it in a thread so we don't block the event loop
    payload = await asyncio.to_thread(get_video_comments_with_metrics, video_id)

    # Persist
    file_path = _cache_file_path(video_id)
    _safe_write_json(file_path, payload)
    await _upsert_cache_row(video_id, file_path, now)

    payload.setdefault("_cache", {})
    payload["_cache"].update({"hit": False, "fetched_at": now.isoformat(), "age_hours": 0.0})
    return payload
