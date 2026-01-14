from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class FinalSynthesisValidationLogger:
    """Persist validation attempts to disk.

    We intentionally log to files (not DB) because the project already ships with
    file-based AI interaction logs and module validation logs.
    """

    @staticmethod
    def save(
        *,
        video_id: str,
        attempt: int,
        validation_result: Any,
        raw_report_path: Optional[str] = None,
        corrected_report_path: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        logs_dir = Path("validation_logs") / "final_synthesis" / str(video_id)
        logs_dir.mkdir(parents=True, exist_ok=True)

        payload: Dict[str, Any] = {
            "validator": "final_synthesis",
            "attempt": attempt,
            "timestamp": datetime.now().isoformat(),
            "raw_report_path": raw_report_path,
            "corrected_report_path": corrected_report_path,
        }

        # dataclass -> dict
        try:
            payload["result"] = asdict(validation_result)  # type: ignore[arg-type]
        except Exception:
            payload["result"] = validation_result

        if extra:
            payload["extra"] = extra

        out_path = logs_dir / f"final_synthesis_validation_attempt{attempt}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out_path)
