"""Лист rptg.plan.route.decide — назначение оператора: правило, ручное, таблица компетенций,
прикидка (LOGIC §6.4–§6.6).

Функции приняты по карточке design/rptg.plan.route.yaml; обвязку пишет скрипт. Цена на успех —
десятичная запись: модуль decimal узлу не разрешён, сравнение точное — в целых с общим масштабом.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Assignment

if TYPE_CHECKING:
    from rptg._types import Candidate, Competence, Config, Override


def table(candidate: Candidate, manual: Override, table: Competence, cfg: Config) -> str:
    """Оператор по таблице компетенций или пусто: у архитектора и при ручном операторе роли — пусто;
    клетки класса кандидата при G0, иначе сумма клеток оператора по всем классам (цена на успех —
    взвешенная по всем успехам клетки, подбор и проверка, «мало данных» — сумма выборки подбора и
    проверки меньше n_min: так клетку определяет bench, К-4); годен оператор лестницы роли без пометки
    «мало данных» с долей успеха на подборе ≥ target и на проверке ≥ target − 0,1; берётся самый
    дешёвый на успех, при равенстве — ниже по лестнице."""
    role = candidate.role
    if role == "architect" or getattr(manual, role, None):
        return ""
    ladder, target = getattr(cfg.roles, role), cfg.routing.target

    def num(text):
        whole, _, frac = text.lstrip("-").partition(".")
        return (-1 if text.startswith("-") else 1) * int(whole + (frac + "0" * 18)[:18])

    def cells_of(op):
        return [c for c in table.cells if c.operator == op and (c.class_ == candidate.class_ or not table.g0)]

    def judge(op):
        cells = cells_of(op)
        n_fit, ok_fit, n_check, ok_check = (sum(getattr(c, k) for c in cells) for k in ("n_fit", "ok_fit", "n_check", "ok_check"))
        low = any(c.low_data for c in cells) if table.g0 else n_fit + n_check < cfg.routing.n_min
        fit = ok_fit > 0 and n_check > 0 and not low and ok_fit / n_fit >= target and ok_check / n_check >= target - 0.1
        weight = sum(num(c.cost_per_success) * (c.ok_fit + c.ok_check) for c in cells)
        return (weight // (ok_fit + ok_check), ladder.index(op), op) if fit else None

    ranked = [x for x in map(judge, ladder) if x]
    return min(ranked)[2] if ranked else ""


def assign(candidate: Candidate, manual: Override, choice: str, cfg: Config) -> Assignment:
    """Архитектор — ступень по правилу (start_rung, иначе первая), источник rule; ручной оператор
    роли из лестницы — его ступень, manual; выбор таблицы не пуст — его ступень, table; иначе
    ступень = 1 + число границ роли не выше прикидки, prior; ступень зажимается в
    start_rung..max_rung и длину лестницы."""
    role = candidate.role
    ladder, mine = getattr(cfg.roles, role), getattr(manual, role, None) if role != "architect" else None
    if role == "architect":
        rung, by = manual.start_rung or 1, "rule"
    elif mine in ladder:
        rung, by = ladder.index(mine) + 1, "manual"
    elif choice:
        rung, by = ladder.index(choice) + 1, "table"
    else:
        rung, by = 1 + sum(1 for b in getattr(cfg.routing.prior_bands, role) if b <= candidate.prior), "prior"
    rung = min(max(rung, manual.start_rung or 1), manual.max_rung or len(ladder), len(ladder))
    return Assignment(subject=candidate.subject, role=role, class_=candidate.class_, operator=ladder[rung - 1], rung=rung,
                      decided_by=by)
