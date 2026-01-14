from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from database.crud import (
    get_active_multi_analysis_prompt,
    get_due_video_analysis_sets,
    get_final_advanced_analyses_for_set,
    mark_pdf_deleted_for_analysis,
    save_multi_analysis_evaluation,
)
from services.analysis_evaluator import evaluate_analyses_via_ai


def _pick_best_analysis_id(evaluations: List[Dict[str, Any]]) -> int:
    """Pick best analysis id using evaluator ranks/scores."""
    # Prefer quality_rank=1
    ranked = [e for e in evaluations if isinstance(e, dict) and e.get("quality_rank") is not None]
    if ranked:
        try:
            best = sorted(ranked, key=lambda x: int(x.get("quality_rank") or 999))[0]
            return int(best["analysis_id"])
        except Exception:
            pass

    # Fallback: max total_score
    scored = [e for e in evaluations if isinstance(e, dict) and isinstance(e.get("total_score"), (int, float))]
    if scored:
        best = max(scored, key=lambda x: float(x["total_score"]))
        return int(best["analysis_id"])

    # Last resort: first
    return int(evaluations[0]["analysis_id"])


async def _delete_pdf_best_effort(pdf_path: str | None) -> bool:
    if not pdf_path:
        return False
    try:
        p = Path(pdf_path)
        if p.exists() and p.is_file():
            p.unlink()
            return True
    except Exception:
        return False
    return False


async def run_multi_analysis_optimizer_once() -> int:
    """One optimizer iteration. Returns number of evaluated sets."""
    prompt = await get_active_multi_analysis_prompt()
    if not prompt:
        return 0

    sets = await get_due_video_analysis_sets(limit=25)
    evaluated = 0

    for s in sets:
        analyses_rows = await get_final_advanced_analyses_for_set(s.id)
        if len(analyses_rows) < 3:
            continue

        analyses = [
            {
                "analysis_id": a.id,
                "created_at": a.created_at,
                "text": a.response_text,
                "pdf_file_path": a.pdf_file_path,
            }
            for a in analyses_rows
        ]

        try:
            eval_result, evaluations = await evaluate_analyses_via_ai(
                user_id=int(s.user_id),
                youtube_video_id=s.video_id,
                video_title=None,
                analyses=analyses,
                prompt_template=prompt.prompt_text,
            )
        except Exception as e:
            # Mark set as error (best-effort)
            try:
                from database.engine import async_session
                from sqlalchemy import update
                from database.models import VideoAnalysisSet

                async with async_session() as session:
                    await session.execute(
                        update(VideoAnalysisSet)
                        .where(VideoAnalysisSet.id == s.id)
                        .values(status="error", evaluation_result={"error": str(e)})
                    )
                    await session.commit()
            except Exception:
                pass
            continue

        best_analysis_id = int(eval_result.get("best_analysis_id") or 0)
        valid_ids = {a["analysis_id"] for a in analyses}
        if best_analysis_id not in valid_ids:
            best_analysis_id = _pick_best_analysis_id(evaluations)

        # Derive PDFs to delete (quality_rank>1 OR not best)
        to_delete = [a for a in analyses if a["analysis_id"] != best_analysis_id]

        # Persist evaluation + markers
        eval_result_enriched = dict(eval_result)
        eval_result_enriched["optimizer"] = {
            "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
            "best_analysis_id": best_analysis_id,
            "pdfs_to_delete": [a["analysis_id"] for a in to_delete],
        }

        await save_multi_analysis_evaluation(
            analysis_set_id=s.id,
            best_analysis_id=best_analysis_id,
            evaluation_result=eval_result_enriched,
            evaluations=evaluations,
        )

        # Delete non-best PDFs
        for a in to_delete:
            ok = await _delete_pdf_best_effort(a.get("pdf_file_path"))
            if ok:
                await mark_pdf_deleted_for_analysis(s.id, int(a["analysis_id"]))

        evaluated += 1

    return evaluated


async def run_multi_analysis_optimizer_scheduler(interval_seconds: int = 1800):
    """Background scheduler. interval_seconds=1800 by default (30 minutes)."""
    while True:
        try:
            await run_multi_analysis_optimizer_once()
        except Exception:
            # Do not crash background task
            pass
        await asyncio.sleep(interval_seconds)
