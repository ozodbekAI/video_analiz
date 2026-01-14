from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from services.ai_service import analyze_text_with_prompt, save_ai_interaction


def _extract_json_block(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response."""
    if not text:
        raise ValueError("Empty evaluator response")

    # Fast path
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # Try to locate the first top-level JSON object
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in evaluator response")
    return json.loads(m.group(0))


def build_analyses_content(analyses: List[Dict[str, Any]], max_chars: int = 2000) -> str:
    """Format analyses into the TZ-2 prompt block."""
    parts: List[str] = []
    for a in analyses:
        analysis_id = a["analysis_id"]
        created_at = a.get("created_at")
        created_at_str = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        text_report = (a.get("text") or "").strip()
        snippet = text_report[:max_chars]

        parts.append(
            "\n".join(
                [
                    f"АНАЛИЗ #{analysis_id} (от {created_at_str}):",
                    "### VIDEO_ANALYSIS_REPORT_START ###",
                    snippet,
                    "### VIDEO_ANALYSIS_REPORT_END ###",
                    "",
                ]
            )
        )
    return "\n".join(parts).strip()


def _safe_replace(template: str, mapping: Dict[str, str]) -> str:
    out = template
    for k, v in mapping.items():
        out = out.replace("{" + k + "}", v)
    return out


async def evaluate_analyses_via_ai(
    *,
    user_id: int,
    youtube_video_id: str,
    video_title: str | None,
    analyses: List[Dict[str, Any]],
    prompt_template: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run TZ-2 evaluator prompt and return (full_result_json, evaluations_list)."""
    if len(analyses) < 3:
        raise ValueError("Need at least 3 analyses to evaluate")

    created_times = [a.get("created_at") for a in analyses if a.get("created_at")]
    if created_times:
        start = min(created_times)
        end = max(created_times)
        period = f"{start.isoformat()} .. {end.isoformat()}"
    else:
        period = "unknown"

    analyses_content = build_analyses_content(analyses)

    filled_prompt = _safe_replace(
        prompt_template,
        {
            "video_id": youtube_video_id,
            "video_title": video_title or "Unknown",
            "total_analyses": str(len(analyses)),
            "analysis_period": period,
            "analyses_content": analyses_content,
        },
    )

    # Important: do not distort report text; send it as-is.
    response_text = await analyze_text_with_prompt(
        "Сформируй ответ строго в JSON по заданному формату.",
        filled_prompt,
        max_tokens=2200,
        temperature=0.15,
    )

    save_ai_interaction(
        user_id=user_id,
        video_id=youtube_video_id,
        stage="multi_analysis_evaluation",
        request_text=filled_prompt,
        response_text=response_text,
    )

    result = _extract_json_block(response_text)
    evaluations = result.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        raise ValueError("Evaluator JSON missing 'evaluations' list")

    # Normalize evaluations
    normalized: List[Dict[str, Any]] = []
    for ev in evaluations:
        if not isinstance(ev, dict):
            continue
        if "analysis_id" not in ev:
            continue
        try:
            ev["analysis_id"] = int(ev["analysis_id"])
        except Exception:
            continue

        # total_score normalization
        ts = ev.get("total_score")
        if ts is None:
            scores = ev.get("scores") or {}
            if isinstance(scores, dict) and scores:
                vals = [float(v) for v in scores.values() if isinstance(v, (int, float))]
                ev["total_score"] = round(sum(vals) / len(vals), 3) if vals else None
        normalized.append(ev)

    if not normalized:
        raise ValueError("Evaluator JSON has no valid evaluation entries")

    result["evaluations"] = normalized
    return result, normalized
