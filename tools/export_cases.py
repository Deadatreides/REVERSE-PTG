"""Выгрузка контрольных случаев проверок (tests/test_check_controls.py, CASES) в rptg_host/control_cases.json —
данные для `rptg selftest`: по итогу оболочка пишет доверенные проверки (Config.trusted).

    python tools/export_cases.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import test_check_controls as controls  # noqa: E402

cases = [{"id": i, "check": c, "input": given, "expected": expected} for i, c, given, expected in controls.CASES]
out = ROOT / "rptg_host" / "control_cases.json"
out.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
print(f"{len(cases)} случаев → {out}")
