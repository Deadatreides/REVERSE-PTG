"""Лист rptg.lang.cl.logic.solve — единственный лист, который вызывает z3.

Функции приняты по карточке design/rptg.lang.cl.logic.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl.logic._types import SolveResult

if TYPE_CHECKING:
    from rptg._types import Limits
    from rptg.lang.cl.logic._types import SmtText


def run(smt: SmtText, limits: Limits) -> SolveResult:
    """Решить текст SMT-LIB; неготовый текст или отсутствие z3 — unknown с причиной.

    Предел — rlimit, а не время: один и тот же текст даёт один и тот же ответ на любой машине
    (находка С-6). Модель — символ → значение текстом: целое "5", вещественное "1/2",
    логическое "true", строка — как есть. Ядро — имена утверждений по порядку.
    """
    if not smt.ok:
        return SolveResult(status="unknown", model={}, core=[], reason="текст SMT не готов: " + "; ".join(smt.errors))
    try:
        import z3
    except ImportError:
        return SolveResult(status="unknown", model={}, core=[], reason="z3 не установлен")
    solver = z3.Solver()
    solver.set("rlimit", limits.z3_rlimit)
    solver.set("unsat_core", True)
    solver.from_string(smt.text)
    answer = solver.check()
    if answer == z3.unsat:
        return SolveResult(status="unsat", model={}, core=sorted(str(c) for c in solver.unsat_core()))
    if answer != z3.sat:
        return SolveResult(status="unknown", model={}, core=[], reason=solver.reason_unknown())
    model = solver.model()

    def text(v):
        if z3.is_int_value(v):
            return str(v.as_long())
        if z3.is_rational_value(v):
            num, den = v.numerator_as_long(), v.denominator_as_long()
            return str(num) if den == 1 else f"{num}/{den}"
        if z3.is_true(v) or z3.is_false(v):
            return "true" if z3.is_true(v) else "false"
        return v.as_string() if z3.is_string_value(v) else str(v)

    return SolveResult(status="sat", model={d.name(): text(model[d]) for d in model.decls()}, core=[])
