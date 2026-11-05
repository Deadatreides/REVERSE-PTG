"""Лист rptg.plan.route.prior — класс работы (LOGIC §6.3) и априорная оценка (§6.5) по мерам: две
работы, две операции (после Э1 01.10.2026: в одной функции решений было 30 при допуске 24,5).

Функции приняты по карточке design/rptg.plan.route.yaml; обвязку пишет скрипт. Формулы прикидки
перенесены из прототипа tools/selfcheck.py без изменений; на продуктовых листьях lang они дают
числа LOGIC §6.9 — 8, 13, 15 (допущение А1: веса не измерены, у формулы одна задача — разумный старт).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Candidate

if TYPE_CHECKING:
    from rptg._types import Candidates, Config, Json, Strings
    from rptg.plan._types import Ready
    from rptg.plan.route._types import Overrides, RouteCounts, RouteInfos


def classes(state: Json, ready: Ready, infos: RouteInfos) -> Strings:
    """Карта и архитектор — map, сборка и разложение — design; функция — по первому признаку:
    эффекты — io, арифметика в ensures — compute, кванторы и агрегаты — search, строки в параметрах,
    результате или условиях — text, иначе transform; меры условий — по порядку заданий."""
    told, out = iter(infos), []

    def of_function(op, mine):
        strings = "string" in [p["type"] for p in op["params"]] + [op["result"]] or any(i.strings for i in mine)
        flags = [("io", bool(op["effects"])), ("compute", any(i.arith for i in mine[len(op["requires"]):])),
                 ("search", any(i.quant for i in mine)), ("text", strings)]
        return next((name for name, hit in flags if hit), "transform")

    for r in ready:
        measured = r.role != "architect" and r.kind in ("function", "design")
        ops = [o for o in state["cards"][r.node]["ops"] if r.kind == "design" or o["name"] == r.op] if measured else []
        got = [[next(told) for _ in o["requires"] + o["ensures"]] for o in ops]
        out.append(of_function(ops[0], got[0]) if r.kind == "function" else "map" if r.role == "architect" else "design")
    return out


def candidates(state: Json, ready: Ready, infos: RouteInfos, sizes: RouteCounts, manual: Overrides, classes: Strings,
               cfg: Config) -> Candidates:
    """Кандидат на каждый готовый элемент с его классом: карта, разложение корня (архитектор) и сборки
    — оценка 0; разложение — S_раз по всем операциям узла; функция — S_исп; меры и размеры берутся по
    порядку заданий; est_lines заменяет ручное назначение."""
    told, sized = iter(infos), iter(sizes)

    def sat(value, full):
        return min(1, value / full)

    def design_prior(card, ops, measures, est):
        flat = [i for g, _ in measures for i in g]
        text = (len(card["purpose"]) + sum(len(o["doc"]) for o in ops)) / 4
        effects = len({e for o in ops for e in o["effects"]} | set(card["effects"]))
        parts = [3 * sat(len(ops) - 1, 7), 2 * sat(sum(t for _, t in measures), 80), 2 * sat(sum(i.nodes for i in flat), 120),
                 sat(sum(i.quant for i in flat), 6), sat(effects, 3), 2 * sat(len(card["uses"]), 6), 4 * sat(est, 1000),
                 2 * sat(text, 600)]
        return round(100 * sum(parts) / 17)

    def function_prior(card, op, measure, est):
        mine, tsize = measure
        parts = [3 * sat(sum(i.nodes for i in mine), 60), 2 * sat(sum(i.quant for i in mine), 4), sat(sum(i.nonlin for i in mine), 2),
                 2 * sat(tsize, 40), sat(len(op["effects"]), 3), 3 * sat(est / len(card["ops"]), cfg.limits.final_max_lines),
                 sat((len(op["doc"]) + len(card["purpose"])) / 4, 300)]
        return round(100 * sum(parts) / 13)

    def one(r, m, klass):
        if r.role == "architect" or r.kind not in ("function", "design"):
            return Candidate(subject=r.subject, kind=r.kind, role=r.role, class_=klass, prior=0, level=r.level)
        card = state["cards"][r.node]
        ops = [o for o in card["ops"] if r.kind == "design" or o["name"] == r.op]
        measures = [([next(told) for _ in o["requires"] + o["ensures"]], sum(next(sized) for _ in range(len(o["params"]) + 1)))
                    for o in ops]
        est = m.est_lines or card["est_lines"]
        prior = design_prior(card, ops, measures, est) if r.kind == "design" else function_prior(card, ops[0], measures[0], est)
        return Candidate(subject=r.subject, kind=r.kind, role=r.role, class_=klass, prior=prior, level=r.level)

    return [one(r, m, klass) for r, m, klass in zip(ready, manual, classes)]
