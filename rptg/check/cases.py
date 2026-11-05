"""Лист rptg.check.cases — контрольные случаи проверок: вход конвейера, вердикт случая, сводка.

Функции приняты по карточке design/rptg.check.yaml; обвязку пишет скрипт. Случай гонится через
тот же конвейер, что и событие (evaluate): контрольные случаи проверяют код, работающий в деле.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import CaseResult, SelftestReport, SelftestReportChecksItem
from rptg.check._types import CaseInput

if TYPE_CHECKING:
    from rptg._types import CaseResults, ControlCase, Evidences


def unpack(case: ControlCase) -> CaseInput:
    """Полный вид {state, event} идёт как есть; вид ребра П3 {source_type, target_type, env} — в
    edges при пустых состоянии и событии: такой случай проверяет только подтип."""
    given = case.input if isinstance(case.input, dict) else {}
    if "source_type" in given:
        return CaseInput(state={}, event={}, edges=[given])
    return CaseInput(state=given.get("state") or {}, event=given.get("event") or {},
                     edges=given.get("edges") or [])


def pick(case: ControlCase, evidences: Evidences) -> CaseResult:
    """Вердикт проверки случая: провал любого её доказательства — fail, иначе unknown любого —
    unknown, иначе pass; доказательств этой проверки нет — unknown (проверка промолчала)."""
    verdicts = {e.verdict for e in evidences if e.check == case.check}
    if "fail" in verdicts:
        actual = "fail"
    elif "unknown" in verdicts or not verdicts:
        actual = "unknown"
    else:
        actual = "pass"
    return CaseResult(id=case.id, check=case.check, expected=case.expected, actual=actual,
                      ok=actual == case.expected)


def summarize(results: CaseResults) -> SelftestReport:
    """Сводка по проверкам в порядке слоёв: сколько случаев сошлось, какие нет; доверенная —
    та, у которой не разошёлся ни один."""
    order = ["P1", "P2", "P3", "P4", "P5", "P7", "E1", "E2", "E3", "E6"]
    rows: dict = {}
    for r in results:
        row = rows.setdefault(r.check, {"passed": 0, "failed": 0, "failures": []})
        if r.ok:
            row["passed"] += 1
        else:
            row["failed"] += 1
            row["failures"].append(r.id)
    checks = [SelftestReportChecksItem(check=c, passed=v["passed"], failed=v["failed"],
                                       trusted=v["failed"] == 0, failures=v["failures"])
              for c, v in sorted(rows.items(), key=lambda kv: order.index(kv[0]))]
    return SelftestReport(checks=checks)
