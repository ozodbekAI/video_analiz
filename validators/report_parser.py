from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


_HEADING_RE = re.compile(r"^\s*#{2,6}\s*(.+?)\s*#*\s*$")
_MARKER_RE = re.compile(r"###\s*([A-ZА-Я_\- ]{6,})\s*###")


@dataclass
class ParsedReport:
    """Best-effort structured representation of the final synthesis report."""

    raw: str
    markers: Dict[str, int] = field(default_factory=dict)  # marker -> position
    headings: Dict[str, str] = field(default_factory=dict)  # heading -> content
    strategic_meta: Dict[str, str] = field(default_factory=dict)
    video_meta: Dict[str, str] = field(default_factory=dict)
    comments_analysis: Dict[str, str] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)


def normalize_cyrillic_ve(text: str) -> str:
    """Fix common 'B' vs 'В' typo in Russian headers."""
    # Replace Latin B only in the word 'КОММЕНТАРИЕB' or similar.
    return re.sub(r"КОММЕНТАРИЕB", "КОММЕНТАРИЕВ", text)


def extract_markers(text: str) -> Dict[str, int]:
    markers: Dict[str, int] = {}
    for m in re.finditer(r"###\s*([A-ZА-Я_\-]+)\s*###", text):
        markers[m.group(1).strip()] = m.start()
    # Also capture START/END markers without ### in spec (VIDEO_ANALYSIS_METRICS_START/END)
    for m in re.finditer(r"\b(VIDEO_ANALYSIS_(?:REPORT|METRICS)_(?:START|END))\b", text):
        markers[m.group(1)] = m.start()
    return markers


def split_by_headings(text: str) -> Dict[str, str]:
    """Split by markdown headings like '### ... ###' or '### ...'"""
    lines = text.splitlines()
    result: Dict[str, List[str]] = {}
    current_key: Optional[str] = None

    for line in lines:
        m = _MARKER_RE.search(line)
        if m:
            current_key = m.group(1).strip()
            result.setdefault(current_key, [])
            continue
        # Also accept markdown headings (## ...)
        mh = _HEADING_RE.match(line)
        if mh and mh.group(1).strip().upper() in {
            "СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ",
            "МЕТАДАННЫЕ ВИДЕО",
            "АНАЛИЗ КОММЕНТАРИЕВ",
            "КРОСС-МОДУЛЬНЫЕ СТРАТЕГИЧЕСКИЕ ИНСАЙТЫ",
            "ДАННЫЕ ДЛЯ АГРЕГАЦИИ",
            "ВЫВОДЫ ДЛЯ ПАТТЕРНОГО АНАЛИЗА",
            "АЛГОРИТМИЧЕСКИЕ ДАННЫЕ",
            "ПРОИЗВОДСТВЕННЫЕ ДАННЫЕ",
            "КОМПАРАТИВНЫЙ АНАЛИЗ",
        }:
            current_key = mh.group(1).strip().upper()
            result.setdefault(current_key, [])
            continue

        if current_key is not None:
            result[current_key].append(line)

    return {k: "\n".join(v).strip() for k, v in result.items()}


def _parse_kv_block(block: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().upper()
        val = val.strip()
        if not key:
            continue
        out[key] = val
    return out


def parse_report(raw_report: str) -> ParsedReport:
    raw_report = normalize_cyrillic_ve(raw_report)
    markers = extract_markers(raw_report)
    sections = split_by_headings(raw_report)

    strategic_meta = {}
    video_meta = {}
    comments_analysis = {}
    insights: List[str] = []

    # Strategic meta
    if "СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ" in sections:
        strategic_meta = _parse_kv_block(sections["СТРАТЕГИЧЕСКИЕ МЕТА-ДАННЫЕ"])
    # Video meta
    if "МЕТАДАННЫЕ ВИДЕО" in sections:
        video_meta = _parse_kv_block(sections["МЕТАДАННЫЕ ВИДЕО"])
    # Comments analysis
    if "АНАЛИЗ КОММЕНТАРИЕВ" in sections:
        comments_analysis = _parse_kv_block(sections["АНАЛИЗ КОММЕНТАРИЕВ"])
    # Insights
    if "КРОСС-МОДУЛЬНЫЕ СТРАТЕГИЧЕСКИЕ ИНСАЙТЫ" in sections:
        # Split insights by marker like [ИНСАЙТ ...] or **[ИНСАЙТ ...]**
        text = sections["КРОСС-МОДУЛЬНЫЕ СТРАТЕГИЧЕСКИЕ ИНСАЙТЫ"]
        parts = re.split(r"\n\s*(?:\*\*)?\[ИНСАЙТ[\s_\-]*\d+\](?:\*\*)?\s*:?\s*", text, flags=re.IGNORECASE)
        # parts[0] is intro; rest are insights bodies
        for body in parts[1:]:
            body = body.strip()
            if body:
                insights.append(body)

    return ParsedReport(
        raw=raw_report,
        markers=markers,
        headings=sections,
        strategic_meta=strategic_meta,
        video_meta=video_meta,
        comments_analysis=comments_analysis,
        insights=insights,
    )
