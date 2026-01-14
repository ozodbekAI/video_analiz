from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .corrector import auto_correct_report
from .formulas import calculate_expected_chi, calculate_expected_ssi
from .modules_data_extractor import extract_ids_by_type, extract_modules_data
from .report_parser import ParsedReport, parse_report


@dataclass
class ValidationIssue:
    type: str
    severity: str  # LOW/MEDIUM/HIGH
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinalSynthesisValidationResult:
    status: str  # PASS/FAIL
    score: int
    issues: List[ValidationIssue]
    mode: str
    corrected_report: Optional[str] = None
    retry_needed: bool = False
    retry_prompt: Optional[str] = None
    indices_calculated: Dict[str, Any] = field(default_factory=dict)


class FinalSynthesisValidator:
    """Validator for the final synthesis report generated after module 10-5.

    The validator enforces the 'VIDEO_ANALYSIS_REPORT' structure described in
    the provided TЗ and performs:
      - Structure checks (mandatory markers/sections, order)
      - Completeness checks (required fields)
      - Consistency checks (ID referential integrity, percentages)
      - Index checks (CHI/SSI formulas)
      - Insight checks (count and required links)
      - Adaptive mode rules (A/Б/В)
    """

    REQUIRED_MARKERS = [
        "VIDEO_ANALYSIS_REPORT_START",
        "VIDEO_ANALYSIS_REPORT_END",
        "VIDEO_ANALYSIS_METRICS_START",
        "VIDEO_ANALYSIS_METRICS_END",
    ]
    REQUIRED_SECTIONS = [
        "СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ",
        "МЕТАДАННЫЕ ВИДЕО",
        "АНАЛИЗ КОММЕНТАРИЕВ",
        "КРОСС-МОДУЛЬНЫЕ СТРАТЕГИЧЕСКИЕ ИНСАЙТЫ",
        "ДАННЫЕ ДЛЯ АГРЕГАЦИИ",
    ]

    def __init__(self, *, chi_tolerance_points: float = 10.0, ssi_tolerance: float = 0.5):
        self.chi_tolerance_points = chi_tolerance_points
        self.ssi_tolerance = ssi_tolerance

    @staticmethod
    def _severity_penalty(sev: str) -> int:
        sev = sev.upper().strip()
        return {"LOW": 5, "MEDIUM": 15, "HIGH": 30}.get(sev, 10)

    @staticmethod
    def _extract_mode(parsed: ParsedReport) -> str:
        # Strategic meta preferred
        for key in ("ANALYSIS_MODE", "РЕЖИМ", "MODE"):
            if key in parsed.strategic_meta:
                return str(parsed.strategic_meta.get(key)).strip()
        # Fallback: detect 'Режим А/Б/В' in raw
        m = re.search(r"Режим\s*([АAБBВV])", parsed.raw, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
        return "В"

    @staticmethod
    def _extract_float_from_meta(meta: Dict[str, str], key: str) -> Optional[float]:
        if key not in meta:
            return None
        val = str(meta.get(key) or "").strip()
        val = val.replace("%", "").replace(",", ".")
        try:
            return float(re.findall(r"-?\d+(?:\.\d+)?", val)[0])
        except Exception:
            return None

    @staticmethod
    def _extract_tone_percentages(raw: str) -> Dict[str, float]:
        # Look for lines: 'Положительные: 65%' etc
        out: Dict[str, float] = {}
        for label in ("Положительные", "Нейтральные", "Негативные"):
            m = re.search(rf"{label}\s*:\s*(\d+(?:[\.,]\d+)?)\s*%", raw, flags=re.IGNORECASE)
            if m:
                out[label] = float(m.group(1).replace(",", "."))
        return out

    @staticmethod
    def _extract_comment_count_from_report(raw: str) -> Optional[int]:
        # 'Комментарии: 1500' or 'Комментариев: 1500'
        m = re.search(r"Комментар(?:ии|иев)\s*:\s*(\d{1,9})", raw, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        return None

    @staticmethod
    def _collect_ids_from_report(raw: str) -> Dict[str, Set[str]]:
        # Accept both bracketed and plain mentions
        ids = extract_ids_by_type(raw)
        return {k: set(v) for k, v in ids.items()}

    def validate(
        self,
        *,
        raw_report: str,
        video_meta: Dict[str, Any],
        partial_responses: Optional[Dict[str, str]] = None,
    ) -> FinalSynthesisValidationResult:
        parsed = parse_report(raw_report)
        mode = self._extract_mode(parsed)
        video_id = str(video_meta.get("id") or video_meta.get("video_id") or "").strip()

        issues: List[ValidationIssue] = []

        # --- Structure checks (F1)
        for marker in self.REQUIRED_MARKERS:
            if marker not in parsed.markers:
                issues.append(ValidationIssue(
                    type="MISSING_MARKER",
                    severity="HIGH",
                    message=f"Отсутствует обязательный маркер: {marker}",
                    details={"marker": marker},
                ))

        for sec in self.REQUIRED_SECTIONS:
            if sec not in parsed.headings:
                issues.append(ValidationIssue(
                    type="MISSING_SECTION",
                    severity="HIGH",
                    message=f"Отсутствует обязательный раздел: {sec}",
                    details={"section": sec},
                ))

        # Comments analysis header 'В' check
        if "АНАЛИЗ КОММЕНТАРИЕB" in raw_report:
            issues.append(ValidationIssue(
                type="CYRILLIC_VE_TYPO",
                severity="LOW",
                message="В заголовке 'АНАЛИЗ КОММЕНТАРИЕВ' использована латинская 'B' вместо 'В'",
            ))

        # Order check (simplified): ensure major headings appear in expected order
        expected_order = [
            "СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ",
            "МЕТАДАННЫЕ ВИДЕО",
            "АНАЛИЗ КОММЕНТАРИЕВ",
            "КРОСС-МОДУЛЬНЫЕ СТРАТЕГИЧЕСКИЕ ИНСАЙТЫ",
            "ДАННЫЕ ДЛЯ АГРЕГАЦИИ",
        ]
        positions = []
        for sec in expected_order:
            m = re.search(rf"###\s*{re.escape(sec)}\s*###", parsed.raw, flags=re.IGNORECASE)
            positions.append(m.start() if m else 10**9)
        if positions != sorted(positions):
            issues.append(ValidationIssue(
                type="SECTION_ORDER_ERROR",
                severity="MEDIUM",
                message="Нарушен порядок обязательных разделов (ожидается структура промпта 10-5-3)",
                details={"expected": expected_order},
            ))

        # --- Completeness checks (F2)
        required_strategic_fields = [
            "CONTENT_HEALTH_INDEX",
            "AUDIENCE_EVOLUTION_VECTOR",
            "STRATEGIC_STABILITY_INDEX",
            "DATA_QUALITY",
        ]
        for f in required_strategic_fields:
            if f not in parsed.strategic_meta or not str(parsed.strategic_meta.get(f) or "").strip():
                issues.append(ValidationIssue(
                    type="MISSING_FIELD",
                    severity="MEDIUM",
                    message=f"В 'СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ' отсутствует поле: {f}",
                    details={"field": f, "section": "strategic_meta"},
                ))

        if video_id and parsed.video_meta:
            rep_vid = parsed.video_meta.get("ID") or parsed.video_meta.get("VIDEO_ID")
            if rep_vid and str(rep_vid).strip() and str(rep_vid).strip() != video_id:
                issues.append(ValidationIssue(
                    type="VIDEO_ID_MISMATCH",
                    severity="MEDIUM",
                    message="VIDEO_ID в отчёте не совпадает с исходным video_id",
                    details={"expected": video_id, "reported": rep_vid},
                ))

        # Missing-data placeholders
        if re.search(r"\[\s*\]", parsed.raw):
            issues.append(ValidationIssue(
                type="EMPTY_PLACEHOLDER",
                severity="LOW",
                message="В отчёте есть пустые плейсхолдеры '[]' — требуется 'Не указано'/'Нет данных'",
            ))

        # --- Consistency checks (F3)
        tone = self._extract_tone_percentages(parsed.raw)
        if tone:
            s = sum(tone.values())
            if abs(s - 100.0) > 5.0:
                issues.append(ValidationIssue(
                    type="TONE_SUM_ERROR",
                    severity="MEDIUM",
                    message=f"Сумма тональностей должна быть около 100% (сейчас: {s:.1f}%)",
                    details={"tone": tone, "sum": s},
                ))

        # Comment count match (±10%)
        report_comments = self._extract_comment_count_from_report(parsed.raw)
        expected_comments = None
        if isinstance(video_meta.get("comments"), int):
            expected_comments = int(video_meta.get("comments"))
        elif isinstance(video_meta.get("commentCount"), int):
            expected_comments = int(video_meta.get("commentCount"))
        elif isinstance(video_meta.get("comment_count"), int):
            expected_comments = int(video_meta.get("comment_count"))
        if expected_comments and report_comments:
            deviation = abs(report_comments - expected_comments) / max(1, expected_comments)
            if deviation > 0.10:
                issues.append(ValidationIssue(
                    type="COMMENT_COUNT_MISMATCH",
                    severity="LOW",
                    message="Количество комментариев в отчёте существенно отличается от метаданных",
                    details={"reported": report_comments, "expected": expected_comments, "deviation": deviation},
                ))

        # Referential integrity
        modules_data = extract_modules_data(partial_responses or {}) if partial_responses else {"all_ids": {}}
        allowed_ids: Dict[str, Set[str]] = {
            k: set(v) for k, v in (modules_data.get("all_ids") or {}).items()
        }
        referenced = self._collect_ids_from_report(parsed.raw)
        missing_refs: Dict[str, List[str]] = {}
        for k, used in referenced.items():
            if not allowed_ids.get(k):
                continue
            bad = sorted([x for x in used if x not in allowed_ids[k]])
            if bad:
                missing_refs[k] = bad
        if missing_refs:
            issues.append(ValidationIssue(
                type="INVALID_REFERENCES",
                severity="MEDIUM",
                message="В отчёте есть ссылки на ID, отсутствующие во входных данных модулей",
                details={"missing": missing_refs},
            ))

        # --- Indices validation (F4)
        themes = (modules_data.get("10-1") or {}).get("themes", [])
        emotions = (modules_data.get("10-2") or {}).get("emotions", [])
        personas = (modules_data.get("10-3") or {}).get("personas", [])
        risks = (modules_data.get("10-4") or {}).get("risks", [])
        opportunities = (modules_data.get("10-4") or {}).get("opportunities", [])

        reported_chi = self._extract_float_from_meta(parsed.strategic_meta, "CONTENT_HEALTH_INDEX")
        reported_ssi = self._extract_float_from_meta(parsed.strategic_meta, "STRATEGIC_STABILITY_INDEX")

        calculated_chi = calculate_expected_chi(
            mode=mode,
            themes=themes,
            emotions=emotions,
            personas=personas,
            risks=risks,
            critical_signals_pct=None,
            negative_pct=tone.get("Негативные") if tone else None,
        )
        calculated_ssi = calculate_expected_ssi(risks=risks, opportunities=opportunities)

        indices_calculated: Dict[str, Any] = {
            "CONTENT_HEALTH_INDEX": {"reported": reported_chi, "calculated": calculated_chi},
            "STRATEGIC_STABILITY_INDEX": {"reported": reported_ssi, "calculated": calculated_ssi},
        }

        if reported_chi is not None and calculated_chi is not None:
            deviation = abs(reported_chi - calculated_chi)
            if deviation > self.chi_tolerance_points:
                issues.append(ValidationIssue(
                    type="CONTENT_HEALTH_MISMATCH",
                    severity="MEDIUM",
                    message=(
                        f"CONTENT_HEALTH_INDEX не соответствует формуле (указано: {reported_chi:.1f}, "
                        f"расчёт: {calculated_chi:.1f}, отклонение: {deviation:.1f}, допустимо: ±{self.chi_tolerance_points})"
                    ),
                    details={"reported": reported_chi, "calculated": calculated_chi, "deviation": deviation},
                ))

        if reported_ssi is not None and calculated_ssi is not None:
            deviation = abs(reported_ssi - calculated_ssi)
            if deviation > self.ssi_tolerance:
                issues.append(ValidationIssue(
                    type="STRATEGIC_STABILITY_MISMATCH",
                    severity="MEDIUM",
                    message=(
                        f"STRATEGIC_STABILITY_INDEX не соответствует формуле (указано: {reported_ssi:.2f}, "
                        f"расчёт: {calculated_ssi:.2f}, отклонение: {deviation:.2f}, допустимо: ±{self.ssi_tolerance})"
                    ),
                    details={"reported": reported_ssi, "calculated": calculated_ssi, "deviation": deviation},
                ))

        # AUDIENCE_EVOLUTION_VECTOR format
        aev = parsed.strategic_meta.get("AUDIENCE_EVOLUTION_VECTOR")
        if aev and "→" not in aev:
            issues.append(ValidationIssue(
                type="AUDIENCE_VECTOR_FORMAT_ERROR",
                severity="MEDIUM",
                message="AUDIENCE_EVOLUTION_VECTOR должен содержать символ '→'",
                details={"value": aev},
            ))

        # --- Insights validation (F5)
        required_insights = {"A": (3, 5), "А": (3, 5), "B": (2, 3), "Б": (2, 3), "В": (1, 2), "V": (1, 2)}
        lo, hi = required_insights.get(mode.strip().upper(), (1, 2))
        if len(parsed.insights) < lo:
            issues.append(ValidationIssue(
                type="INSIGHTS_TOO_FEW",
                severity="MEDIUM",
                message=f"Недостаточно инсайтов для режима {mode}: нужно минимум {lo}",
                details={"count": len(parsed.insights), "required_min": lo},
            ))
        if len(parsed.insights) > hi:
            issues.append(ValidationIssue(
                type="INSIGHTS_TOO_MANY",
                severity="LOW",
                message=f"Слишком много инсайтов для режима {mode}: рекомендуется не более {hi}",
                details={"count": len(parsed.insights), "recommended_max": hi},
            ))

        # Each insight structure check: must include ThemeID, EmotionID, PersonaID and Risk/Opportunity
        for idx_ins, insight in enumerate(parsed.insights, start=1):
            ids = extract_ids_by_type(insight)
            missing = []
            if not ids.get("ThemeID"):
                missing.append("ThemeID")
            if not ids.get("EmotionID"):
                missing.append("EmotionID")
            if not ids.get("PersonaID"):
                missing.append("PersonaID")
            if not (ids.get("RiskID") or ids.get("OpportunityID")):
                missing.append("RiskID/OpportunityID")
            if missing:
                issues.append(ValidationIssue(
                    type="INSIGHT_STRUCTURE_ERROR",
                    severity="LOW" if len(missing) <= 1 else "MEDIUM",
                    message=f"ИНСАЙТ {idx_ins} не содержит обязательные связи: {', '.join(missing)}",
                    details={"insight": idx_ins, "missing": missing},
                ))

        # Pattern analysis section requirement for mode A
        if mode.strip().upper() in {"A", "А"}:
            if "ВЫВОДЫ ДЛЯ ПАТТЕРНОГО АНАЛИЗА" not in parsed.headings:
                issues.append(ValidationIssue(
                    type="MISSING_PATTERN_SECTION",
                    severity="MEDIUM",
                    message="Для режима А обязателен раздел 'ВЫВОДЫ ДЛЯ ПАТТЕРНОГО АНАЛИЗА'",
                ))

        # --- Decide actions
        score = 100
        for it in issues:
            score -= self._severity_penalty(it.severity)
        score = max(0, min(100, score))

        high_issues = [i for i in issues if i.severity.upper() == "HIGH"]

        # By default, HIGH issues require regeneration, except strictly recoverable
        # formatting issues (missing START/END markers, missing aggregation block).
        missing_sections = [i.details.get("section") for i in high_issues if i.type == "MISSING_SECTION"]
        non_recoverable_missing = [s for s in missing_sections if s and s != "ДАННЫЕ ДЛЯ АГРЕГАЦИИ"]
        retry_needed = bool(high_issues) and bool(non_recoverable_missing or any(i.type != "MISSING_MARKER" and i.type != "MISSING_SECTION" for i in high_issues))
        corrected_report = None

        # Prepare IDs used for aggregation block (best-effort)
        used_ids = {
            "ThemeID": sorted(list(referenced.get("ThemeID", set())))[:50],
            "EmotionID": sorted(list(referenced.get("EmotionID", set())))[:50],
            "PersonaID": sorted(list(referenced.get("PersonaID", set())))[:50],
            "RiskID": sorted(list(referenced.get("RiskID", set())))[:50],
            "OpportunityID": sorted(list(referenced.get("OpportunityID", set())))[:50],
        }
        indices_for_block = {
            "CONTENT_HEALTH_INDEX": calculated_chi if calculated_chi is not None else reported_chi,
            "STRATEGIC_STABILITY_INDEX": calculated_ssi if calculated_ssi is not None else reported_ssi,
        }

        # Auto-correct only strictly safe issues (envelope markers, aggregation JSON, Cyrillic 'В').
        if issues:
            only_recoverable_high = bool(high_issues) and not non_recoverable_missing and all(
                i.type in {"MISSING_MARKER", "MISSING_SECTION"} for i in high_issues
            )
            if not high_issues or only_recoverable_high:
                corr = auto_correct_report(
                    raw_report=parsed.raw,
                    video_id=video_id or "unknown",
                    mode=mode,
                    indices=indices_for_block,
                    used_ids=used_ids,
                )
                if corr.applied:
                    corrected_report = corr.corrected_report
                    # Auto-correction does not override required regeneration for missing semantic sections.
                    if only_recoverable_high:
                        retry_needed = False

        retry_prompt = None
        if retry_needed:
            retry_prompt = self._build_retry_prompt(issues=issues, mode=mode)

        status = "PASS" if (not retry_needed and score >= 70 and not high_issues) else "FAIL"

        return FinalSynthesisValidationResult(
            status=status,
            score=int(score),
            issues=issues,
            mode=mode,
            corrected_report=corrected_report,
            retry_needed=retry_needed,
            retry_prompt=retry_prompt,
            indices_calculated=indices_calculated,
        )

    @staticmethod
    def _build_retry_prompt(*, issues: List[ValidationIssue], mode: str) -> str:
        # Keep it short but prescriptive.
        missing_sections = [i.details.get("section") for i in issues if i.type == "MISSING_SECTION"]
        missing_markers = [i.details.get("marker") for i in issues if i.type == "MISSING_MARKER"]

        must_include = [
            "### VIDEO_ANALYSIS_REPORT_START ###",
            "VIDEO_ANALYSIS_METRICS_START",
            "### СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ ###",
            "### МЕТАДАННЫЕ ВИДЕО ###",
            "### АНАЛИЗ КОММЕНТАРИЕВ ###",
            "### КРОСС-МОДУЛЬНЫЕ СТРАТЕГИЧЕСКИЕ ИНСАЙТЫ ###",
            "### ДАННЫЕ ДЛЯ АГРЕГАЦИИ ### (внутри ```json ...```)",
            "VIDEO_ANALYSIS_METRICS_END",
            "### VIDEO_ANALYSIS_REPORT_END ###",
        ]

        bullets = []
        if missing_markers:
            bullets.append("- Добавь отсутствующие маркеры: " + ", ".join(missing_markers))
        if missing_sections:
            bullets.append("- Добавь отсутствующие разделы: " + ", ".join([s for s in missing_sections if s]))
        # Add main non-structural problems
        for it in issues:
            if it.severity.upper() in {"MEDIUM", "HIGH"} and it.type not in {"MISSING_SECTION", "MISSING_MARKER"}:
                bullets.append(f"- Исправь: {it.message}")

        if mode.strip().upper() in {"A", "А"}:
            bullets.append("- Для режима А обязательно добавь раздел '### ВЫВОДЫ ДЛЯ ПАТТЕРНОГО АНАЛИЗА ###' с рабочими/проблемными элементами.")

        return (
            "Пересобери итоговый отчёт СТРОГО в формате VIDEO_ANALYSIS_REPORT (промпт 10-5-3). "
            f"Режим анализа: {mode}.\n\n"
            "Обязательная структура (в таком порядке):\n"
            + "\n".join(must_include)
            + "\n\nТребуемые исправления:\n"
            + "\n".join(bullets[:15])
            + "\n\nВажно: '### АНАЛИЗ КОММЕНТАРИЕВ ###' — с кириллической буквой 'В'. "
            "Если данных нет — используй 'Не указано' или 'Нет данных'."
        )
