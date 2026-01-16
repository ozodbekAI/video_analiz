from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Set, List


@dataclass
class ActiveAnalysis:
    """Runtime state for a single in-flight analysis (video or shorts).

    Used to support a "Stop analysis" action and to clean up partially created
    DB rows and generated files.
    """

    user_id: int
    chat_id: int
    kind: str  # "video" | "shorts"
    url: str

    started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    youtube_video_id: Optional[str] = None
    db_video_id: Optional[int] = None
    ai_response_ids: List[int] = field(default_factory=list)
    file_paths: Set[str] = field(default_factory=set)

    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task] = None

    def add_file(self, path: str | os.PathLike) -> None:
        if not path:
            return
        self.file_paths.add(str(path))


# Global registry (keyed by Telegram user_id)
ACTIVE_ANALYSES: dict[int, ActiveAnalysis] = {}


def get_active(user_id: int) -> Optional[ActiveAnalysis]:
    a = ACTIVE_ANALYSES.get(int(user_id))
    if not a:
        return None
    if a.task and a.task.done():
        # avoid keeping stale
        ACTIVE_ANALYSES.pop(int(user_id), None)
        return None
    return a


def register_active(a: ActiveAnalysis) -> None:
    ACTIVE_ANALYSES[int(a.user_id)] = a


def unregister_active(user_id: int) -> Optional[ActiveAnalysis]:
    return ACTIVE_ANALYSES.pop(int(user_id), None)


async def cleanup_cancelled_analysis(a: ActiveAnalysis) -> None:
    """Best-effort cleanup for a cancelled analysis.

    Goals:
    - Remove partially created DB rows so downstream features (history, Strategic Hub, TZ-2
      multi-analysis sets) do not see "broken" analyses.
    - Remove generated artifacts (reports, logs, temp files) for the cancelled run.

    Cleanup must be idempotent and must never raise.
    """

    # -----------------
    # DB cleanup
    # -----------------
    try:
        if a.db_video_id is not None:
            # This also unregisters AIResponses from TZ-2 sets.
            from database.crud import delete_video_by_id

            await delete_video_by_id(int(a.db_video_id))
        else:
            # Fallback: if only AIResponse IDs are known
            if a.ai_response_ids:
                from database.crud import delete_ai_response_by_id

                for rid in list(a.ai_response_ids):
                    try:
                        await delete_ai_response_by_id(int(rid))
                    except Exception:
                        pass
    except Exception:
        pass

    # -----------------
    # File cleanup
    # -----------------
    # Start with explicitly tracked artifacts
    paths: Set[str] = set(str(p) for p in list(a.file_paths) if p)

    # Add standard artifacts by convention (extra safety)
    try:
        if a.user_id and a.youtube_video_id:
            uid = str(int(a.user_id))
            vid = str(a.youtube_video_id)

            # Reports
            reports_dir = Path("reports") / uid
            if reports_dir.exists():
                for p in reports_dir.glob(f"{vid}*"):
                    paths.add(str(p))

            # Shorts reports (if any)
            shorts_dir = reports_dir / "shorts"
            if shorts_dir.exists():
                for p in shorts_dir.glob(f"{vid}*"):
                    paths.add(str(p))

            # AI logs
            ai_logs_dir = Path("ai_logs") / uid
            if ai_logs_dir.exists():
                for p in ai_logs_dir.glob(f"*{vid}*"):
                    paths.add(str(p))

            # Temp results (comment dumps)
            results_dir = Path("results")
            if results_dir.exists():
                for p in results_dir.glob(f"{vid}*"):
                    paths.add(str(p))
    except Exception:
        pass

    # Delete files/dirs (delete longer paths first to avoid rmtree on parents)
    for p in sorted(paths, key=lambda x: len(x), reverse=True):
        try:
            if not p:
                continue
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
