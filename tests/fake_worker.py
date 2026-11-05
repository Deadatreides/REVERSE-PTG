"""Поддельный `claude -p` для теста прогона волн: по билету из задания сдаёт верную работу и печатает итог JSON."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

from rptg_kit import server  # noqa: E402
import test_kit as tk  # noqa: E402

args = sys.argv[1:]
prompt = args[args.index("-p") + 1]
model = args[args.index("--model") + 1]
project = re.search(r'project_dir="([^"]+)"', prompt)[1]
ticket = re.search(r"билет (t\d+)", prompt)[1]
target = server.project_of(project).load()["tickets"][ticket]["target"]
work = {"inv.billing": {"files": {"inv/billing/__init__.py": tk.BILLING_WIRED, "inv/billing/lines.py": tk.LINES}},
        "inv.money": {"code": tk.ADD_GOOD}, "inv.billing.lines": {"code": tk.LT_GOOD}}[target]
verdict = server.kit_submit(project, ticket, **work)
print(json.dumps({"result": "принято" if verdict["ok"] else "сдался: " + "; ".join(verdict["report"])[:300],
                  "is_error": not verdict["ok"], "total_cost_usd": 0.001, "usage": {"model": model}}, ensure_ascii=False))
