from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple


def _parse_markdown_table(text: str) -> Tuple[List[str], List[List[str]]]:
    """Parse a simple markdown table into (header, rows).

    This is a best-effort parser designed for AI outputs. It assumes that the
    first table in the provided text is the relevant one.
    """
    lines = [ln.rstrip() for ln in text.splitlines() if "|" in ln]
    if len(lines) < 2:
        return [], []

    # Find the header line (contains letters and pipes, not just separators)
    header_idx = None
    for i, ln in enumerate(lines):
        if re.search(r"[A-Za-zА-Яа-я]", ln) and not re.match(r"^\s*\|?\s*[-: ]+\|", ln):
            header_idx = i
            break
    if header_idx is None or header_idx + 1 >= len(lines):
        return [], []

    header_line = lines[header_idx]
    header = [c.strip() for c in header_line.strip("|").split("|")]

    # Rows start after the separator line (---)
    rows: List[List[str]] = []
    for ln in lines[header_idx + 2 :]:
        if re.match(r"^\s*\|?\s*[-: ]+\|", ln):
            continue
        cols = [c.strip() for c in ln.strip("|").split("|")]
        if len(cols) >= len(header) - 1:
            rows.append(cols)

    return header, rows


def _to_float(val: str) -> Optional[float]:
    try:
        val = val.replace("%", "").replace(",", ".").strip()
        return float(val)
    except Exception:
        return None


def extract_ids_by_type(text: str) -> Dict[str, Set[str]]:
    """Extract ThemeID/EmotionID/PersonaID/RiskID/OpportunityID from arbitrary text."""
    out: Dict[str, Set[str]] = {
        "ThemeID": set(),
        "EmotionID": set(),
        "PersonaID": set(),
        "RiskID": set(),
        "OpportunityID": set(),
    }
    # Matches: [ThemeID: xxx] or ThemeID: xxx
    pattern = re.compile(r"\b(ThemeID|EmotionID|PersonaID|RiskID|OpportunityID)\b\s*:?\s*\[?([^\]\n\r]+)", re.IGNORECASE)
    for m in pattern.finditer(text):
        key = m.group(1)
        val = m.group(2).strip()
        # Stop at common delimiters
        val = re.split(r"[\)\]\|]", val)[0].strip()
        val = val.strip("\"'")
        proper = {
            "themeid": "ThemeID",
            "emotionid": "EmotionID",
            "personaid": "PersonaID",
            "riskid": "RiskID",
            "opportunityid": "OpportunityID",
        }.get(key.lower(), key)
        if val:
            out[proper].add(val)
    return out


def parse_module_10_1(text: str) -> Dict:
    header, rows = _parse_markdown_table(text)
    idx = {h.strip().lower(): i for i, h in enumerate(header)}
    themes: List[Dict] = []
    for r in rows:
        theme_id = r[idx.get("themeid", 0)] if "themeid" in idx else r[0]
        norm_mentions = _to_float(r[idx["norm_mentions"]]) if "norm_mentions" in idx and idx["norm_mentions"] < len(r) else None
        topic_score = _to_float(r[idx["topic_score"]]) if "topic_score" in idx and idx["topic_score"] < len(r) else None
        if theme_id:
            themes.append({
                "ThemeID": theme_id.strip(),
                "norm_mentions": norm_mentions,
                "topic_score": topic_score,
            })
    return {"themes": themes}


def parse_module_10_2(text: str) -> Dict:
    header, rows = _parse_markdown_table(text)
    idx = {h.strip().lower(): i for i, h in enumerate(header)}
    emotions: List[Dict] = []
    for r in rows:
        emotion_id = r[idx.get("emotionid", 0)] if "emotionid" in idx else r[0]
        mentions = _to_float(r[idx["mentions"]]) if "mentions" in idx and idx["mentions"] < len(r) else None
        norm_mentions = _to_float(r[idx["norm_mentions"]]) if "norm_mentions" in idx and idx["norm_mentions"] < len(r) else None
        intensity = _to_float(r[idx["интенсивность"]]) if "интенсивность" in idx and idx["интенсивность"] < len(r) else None
        if emotion_id:
            emotions.append({
                "EmotionID": emotion_id.strip(),
                "mentions": int(mentions) if mentions is not None else 0,
                "norm_mentions": norm_mentions,
                "intensity": intensity,
            })
    return {"emotions": emotions}


def parse_module_10_3(text: str) -> Dict:
    header, rows = _parse_markdown_table(text)
    idx = {h.strip().lower(): i for i, h in enumerate(header)}
    personas: List[Dict] = []
    for r in rows:
        persona_id = r[idx.get("personaid", 0)] if "personaid" in idx else r[0]
        norm_size = _to_float(r[idx["норм.размер"]]) if "норм.размер" in idx and idx["норм.размер"] < len(r) else None
        ivs = _to_float(r[idx["ивс"]]) if "ивс" in idx and idx["ивс"] < len(r) else None
        if persona_id:
            personas.append({
                "PersonaID": persona_id.strip(),
                "segment_size": norm_size,
                "influence_score": ivs,
            })
    return {"personas": personas}


def parse_module_10_4(text: str) -> Dict:
    header, rows = _parse_markdown_table(text)
    idx = {h.strip().lower(): i for i, h in enumerate(header)}

    risks: List[Dict] = []
    opportunities: List[Dict] = []

    for r in rows:
        id_val = r[idx.get("id", 0)] if "id" in idx else r[0]
        type_val = r[idx.get("тип", 1)] if "тип" in idx and len(r) > idx.get("тип", 1) else (r[1] if len(r) > 1 else "")
        iuv = _to_float(r[idx["иув"]]) if "иув" in idx and idx["иув"] < len(r) else None
        pr = r[idx["приоритет"]] if "приоритет" in idx and idx["приоритет"] < len(r) else None

        if not id_val:
            continue
        row_obj = {
            "ID": id_val.strip(),
            "IUV": iuv,
            "priority": pr,
        }
        if str(type_val).strip().lower().startswith("риск"):
            risks.append({"RiskID": id_val.strip(), **row_obj})
        elif str(type_val).strip().lower().startswith("возмож"):
            opportunities.append({"OpportunityID": id_val.strip(), **row_obj})
        else:
            # Unknown type; ignore.
            continue

    return {"risks": risks, "opportunities": opportunities}


def extract_modules_data(partial_responses: Dict[str, str]) -> Dict:
    """Extract structured modules_data from module outputs (10-1..10-4).

    Returns:
        {
          "10-1": {"themes": [...]},
          "10-2": {"emotions": [...]},
          "10-3": {"personas": [...]},
          "10-4": {"risks": [...], "opportunities": [...]},
          "all_ids": {"ThemeID": set(...), ...}
        }
    """
    m10_1 = parse_module_10_1(partial_responses.get("10-1", ""))
    m10_2 = parse_module_10_2(partial_responses.get("10-2", ""))
    m10_3 = parse_module_10_3(partial_responses.get("10-3", ""))
    m10_4 = parse_module_10_4(partial_responses.get("10-4", ""))

    all_ids = {
        "ThemeID": set(),
        "EmotionID": set(),
        "PersonaID": set(),
        "RiskID": set(),
        "OpportunityID": set(),
    }

    # Add parsed table IDs
    for t in m10_1.get("themes", []):
        all_ids["ThemeID"].add(str(t.get("ThemeID")))
    for e in m10_2.get("emotions", []):
        all_ids["EmotionID"].add(str(e.get("EmotionID")))
    for p in m10_3.get("personas", []):
        all_ids["PersonaID"].add(str(p.get("PersonaID")))
    for r in m10_4.get("risks", []):
        all_ids["RiskID"].add(str(r.get("RiskID")))
    for o in m10_4.get("opportunities", []):
        all_ids["OpportunityID"].add(str(o.get("OpportunityID")))

    # Add best-effort IDs from raw content too (covers non-tabular mentions)
    for txt in partial_responses.values():
        extra = extract_ids_by_type(txt)
        for k, s in extra.items():
            all_ids[k].update(s)

    return {
        "10-1": m10_1,
        "10-2": m10_2,
        "10-3": m10_3,
        "10-4": m10_4,
        "all_ids": all_ids,
    }
