"""Лист rptg.check.code.runs — доказательства из отчёта прогона в песочнице (LOGIC §5: Э1–Э3, Э6).

Функции приняты по карточке design/rptg.check.code.yaml; обвязку пишет скрипт. Отчёт пишет
сгенерированный прогонщик: mypy — {errors: [{line, message}]}; examples — [{op, index, ok,
expected, actual, violation, error}]; properties — [{op, ok, examples, counterexample, violation,
too_few}]; violation — первое нарушение трассы обёрток {op: "узел:операция", side, cond, why}.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Config, Evidences, Json


def read(state: Json, event: Json, cfg: Config) -> Evidences:
    """Событие не прогон — пусто. Цель сборки — без вида (корень, build_files): предмет — function:
    и «узел:операция» у функции, assembly: и узел у сборки. mypy — Э1. У функции примеры — Э2, свойства — Э3,
    мало годных входов — unknown. У сборки (node_package, program) примеры и свойства вместе — Э6,
    виновный — по первому нарушению трассы (LOGIC §5, Э6): требование вызываемого — схема узла,
    гарантия вызываемого — он сам (финальный — его функция, составной — его разложение), гарантия
    самого узла — его разложение (дыра П5), результат не тот при чистых условиях — разложение узла.
    Отчёта нет: тайм-аут — fail, иначе unknown."""
    if event.get("kind") != "sandbox_finished":
        return []
    target, output = event["target"], event["output"]
    whole, report = target["kind"] != "function_tests", output.get("report")
    # цель сборки в корне — без вида: «узел:операция» у функции, «узел» у сборки; предмет — с видом
    subject = ("assembly:" if whole else "function:") + target["subject"]
    node = target["subject"] if whole else target["subject"].split(":")[0]

    def one(check, verdict, details, tool="sandbox", counter=None):
        return Evidence(check=check, subject=subject, subject_hash="0" * 64, hard=True, verdict=verdict, details=details,
                        counterexample=counter, tool=tool, trusted=False)

    def blame(v):
        owner = v["op"].partition(":")[0]
        if v["side"] == "requires":
            return f"card:{node}" if owner == node else f"design:{node}"
        if owner == node:
            return f"design:{node}"
        return f"design:{owner}" if owner in state["designs"] else f"function:{v['op']}"

    def failed(check, rows, where):
        bad = [r for r in rows if not r["ok"]]
        if not bad:
            unsure = any(r.get("too_few") for r in rows)
            return one(check, "unknown" if unsure else "pass", {"reason": "мало годных входов"} if unsure else {})
        v = bad[0].get("violation")
        details = {"rule": check, "where": where(bad[0]), "failures": len(bad), "violation": v,
                   "expected": v["cond"] if v else f"результат {json.dumps(bad[0].get('expected'), ensure_ascii=False)}",
                   "actual": json.dumps(bad[0].get("actual"), ensure_ascii=False)}
        if check == "E6":
            details["blame"] = blame(v) if v else f"design:{node}"
        return one(check, "fail", details, counter=bad[0].get("counterexample"))

    def missing():
        reason = "превышено время" if output["timed_out"] else "прогон не дал отчёта"
        return [one(c, "fail" if output["timed_out"] else "unknown", {"reason": reason, "stderr": output.get("stderr_tail", "")})
                for c in (["E6"] if whole else ["E2", "E3"])]

    def mypy():
        errors = [f"строка {e['line']}: {e['message']}" for e in report["mypy"]["errors"]]
        return [one("E1", "fail" if errors else "pass", {"rule": "E1", "where": subject, "problems": errors} if errors else {}, "mypy")]

    def tests():
        examples, props = report.get("examples"), report.get("properties")
        if whole:
            rows = (examples or []) + (props or [])
            return [failed("E6", rows, lambda r: f"{subject}, операция {r['op']}")] if "examples" in report or "properties" in report else []
        out = [failed("E2", examples, lambda r: f"{subject}, пример {r['index']}")] if examples is not None else []
        return out + ([failed("E3", props, lambda r: f"{subject}, свойства {r['op']}")] if props is not None else [])

    if not isinstance(report, dict):
        return missing()
    return (mypy() if "mypy" in report else []) + tests()
