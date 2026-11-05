"""Лист rptg.lang.cl.logic.script — формулы → текст задачи SMT-LIB.

Функции приняты по карточке design/rptg.lang.cl.logic.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl.logic._types import SmtText

if TYPE_CHECKING:
    from rptg._types import Limits
    from rptg.lang.cl.logic._types import SmtTerm, SmtTerms


def prove(facts: SmtTerms, goal: SmtTerm, limits: Limits) -> SmtText:
    """Факты и отрицание цели: «невыполнимо» значит «доказано».

    Объявления — по порядку имён символов, затем неявные факты типов без повторов, затем факты,
    затем отрицание цели и (check-sat). Если хоть одна формула не готова — ok: false с её ошибками.
    """
    parts = list(facts) + [goal]
    errors = [e for p in parts for e in p.errors]
    if not errors and not all(p.ok for p in parts):
        errors = ["формула не готова"]
    sorts: dict = {}
    implicit: list = []
    for p in parts:
        sorts.update(p.sorts)
        implicit += [f for f in p.facts if f not in implicit]
    lines = ["(set-logic ALL)"]
    lines += [f"(declare-const |{s}| {sorts[s]})" for s in sorted(sorts)]
    lines += [f"(assert {f})" for f in implicit]
    lines += [f"(assert {p.term})" for p in facts]
    lines += [f"(assert (not {goal.term}))", "(check-sat)"]
    return SmtText(ok=not errors, errors=errors, text="\n".join(lines) + "\n", kinds=sorts,
                   goal_symbols=sorted(goal.sorts), bound=limits.k_lists)


def sat(conds: SmtTerms, limits: Limits) -> SmtText:
    """Условия под именами c0, c1, … — для ядра противоречия.

    Неявные факты типов идут без имён: ядро называет только строки условий.
    """
    errors = [e for p in conds for e in p.errors]
    if not errors and not all(p.ok for p in conds):
        errors = ["формула не готова"]
    sorts: dict = {}
    implicit: list = []
    for p in conds:
        sorts.update(p.sorts)
        implicit += [f for f in p.facts if f not in implicit]
    lines = ["(set-option :produce-unsat-cores true)", "(set-logic ALL)"]
    lines += [f"(declare-const |{s}| {sorts[s]})" for s in sorted(sorts)]
    lines += [f"(assert {f})" for f in implicit]
    lines += [f"(assert (! {p.term} :named c{i}))" for i, p in enumerate(conds)]
    lines.append("(check-sat)")
    return SmtText(ok=not errors, errors=errors, text="\n".join(lines) + "\n", kinds=sorts,
                   goal_symbols=[], bound=limits.k_lists)
