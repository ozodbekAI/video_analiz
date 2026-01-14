from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def _safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / max(1, len(values))


@dataclass
class CalculatedIndices:
    content_health_index: Optional[float] = None
    strategic_stability_index: Optional[float] = None
    positive_percentage: Optional[float] = None


def calculate_positive_percentage_from_emotions(emotions: List[Dict]) -> Optional[float]:
    """Best-effort positive share from module 10-2 rows.

    Expected row keys: EmotionID, Mentions (int).
    We treat EmotionID containing 'позит' or 'positive' as positive.
    """
    if not emotions:
        return None

    total_mentions = 0.0
    positive_mentions = 0.0
    for row in emotions:
        mentions = float(row.get("mentions") or row.get("Mentions") or 0)
        total_mentions += mentions
        emotion_id = str(row.get("EmotionID") or "").lower()
        if "позит" in emotion_id or "positive" in emotion_id:
            positive_mentions += mentions

    if total_mentions <= 0:
        return None
    return (positive_mentions / total_mentions) * 100.0


def calculate_expected_chi(
    *,
    mode: str,
    themes: List[Dict],
    emotions: List[Dict],
    personas: List[Dict],
    risks: List[Dict],
    critical_signals_pct: Optional[float] = None,
    negative_pct: Optional[float] = None,
) -> Optional[float]:
    """Calculate CONTENT_HEALTH_INDEX (ИЗК) according to the spec.

    Notes:
    - The TЗ describes formulas with TOP-3/TOP-2 inputs for modes A/Б and a
      simplified formula for mode В. Some terms are described as 'Доля ...' in
      the document; in practice we interpret them as "positive emotions share".
    - We normalize Topic_Score to 0..1 by dividing by 100 when values look like
      0..100. When Topic_Score exceeds 100, we cap at 100 for stability.
    - Persona influence (ИВС) from module 10-3 is typically 0..1; we keep it.
    - Risk IUV (ИУВ) from module 10-4 is 0..1.
    """
    mode_norm = (mode or "").strip().upper()
    if mode_norm in {"A", "А"}:
        top_n = 3
        w_topic, w_pos, w_pers, w_risk = 0.25, 0.20, 0.25, 0.30
    elif mode_norm in {"B", "Б"}:
        top_n = 2
        w_topic, w_pos, w_pers, w_risk = 0.30, 0.30, 0.20, 0.20
    else:  # В
        # Mode В: (positive share * 0.5) + ((1 - problem_density) * 0.5)
        pos = calculate_positive_percentage_from_emotions(emotions)
        if pos is None:
            pos = (100.0 - float(negative_pct or 0.0)) if negative_pct is not None else None
        if pos is None:
            return None
        # problem_density: prefer critical_signals_pct; else use negative%.
        if critical_signals_pct is not None:
            problem_density = max(0.0, min(1.0, float(critical_signals_pct) / 100.0))
        elif negative_pct is not None:
            problem_density = max(0.0, min(1.0, float(negative_pct) / 100.0))
        else:
            problem_density = 0.5
        chi = ((pos / 100.0) * 0.50) + ((1.0 - problem_density) * 0.50)
        return max(0.0, min(100.0, chi * 100.0))

    # Mode A/Б
    # Themes
    sorted_themes = sorted(themes, key=lambda r: float(r.get("topic_score", 0) or 0), reverse=True)
    topic_scores = []
    for row in sorted_themes[:top_n]:
        raw = float(row.get("topic_score") or row.get("Topic_Score") or 0.0)
        raw = min(100.0, raw) if raw > 1.5 else raw * 100.0  # heuristic
        topic_scores.append(raw / 100.0)
    avg_topic = _safe_mean(topic_scores)

    # Positive emotions
    pos_pct = calculate_positive_percentage_from_emotions(emotions)
    if pos_pct is None:
        pos_pct = 0.0
    pos_share = max(0.0, min(1.0, pos_pct / 100.0))

    # Personas influence
    sorted_personas = sorted(personas, key=lambda r: float(r.get("influence_score", 0) or 0), reverse=True)
    influence = []
    for row in sorted_personas[:top_n]:
        raw = float(row.get("influence_score") or row.get("ИВС") or 0.0)
        # module 10-3 typically outputs 0..1
        if raw > 1.5:
            raw = min(100.0, raw) / 100.0
        influence.append(raw)
    avg_influence = _safe_mean(influence)

    # Risks IUV
    sorted_risks = sorted(risks, key=lambda r: float(r.get("IUV", 0) or 0), reverse=True)
    iuvs = []
    for row in sorted_risks[:top_n]:
        raw = float(row.get("IUV") or row.get("ИУВ") or 0.0)
        if raw > 1.5:
            raw = min(100.0, raw) / 100.0
        iuvs.append(raw)
    avg_risk_iuv = _safe_mean(iuvs)
    if avg_risk_iuv is None:
        avg_risk_iuv = 0.0

    if avg_topic is None or avg_influence is None:
        return None

    chi_raw = (avg_topic * w_topic) + (pos_share * w_pos) + (avg_influence * w_pers) + ((1.0 - avg_risk_iuv) * w_risk)
    return max(0.0, min(100.0, chi_raw * 100.0))


def calculate_expected_ssi(*, risks: List[Dict], opportunities: List[Dict]) -> Optional[float]:
    """Calculate STRATEGIC_STABILITY_INDEX (ИСУ) according to the spec."""
    num_opps = len(opportunities)
    num_risks = len(risks)
    if num_opps == 0 and num_risks == 0:
        return None

    opp_iuv = []
    for row in opportunities:
        raw = float(row.get("IUV") or row.get("ИУВ") or 0.0)
        if raw > 1.5:
            raw = min(100.0, raw) / 100.0
        opp_iuv.append(raw)
    risk_iuv = []
    for row in risks:
        raw = float(row.get("IUV") or row.get("ИУВ") or 0.0)
        if raw > 1.5:
            raw = min(100.0, raw) / 100.0
        risk_iuv.append(raw)

    avg_opp = _safe_mean(opp_iuv) or 0.0
    avg_risk = _safe_mean(risk_iuv) or 0.0
    # Spec: (opps/(risks+1)) * (avg_opp/(avg_risk+0.1))
    return (num_opps / (num_risks + 1.0)) * (avg_opp / (avg_risk + 0.1))
