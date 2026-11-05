"""Лист rptg.plan.route.measure — задания мер для прикидки (LOGIC §6.5).

Функции приняты по карточке design/rptg.plan.route.yaml; обвязку пишет скрипт. Меры даёт lang — в
окружении каждой операции: окружение без переменных не содержит типов, и размер любого типа в нём
— 1 (замер 30.09.2026: S_раз app.billing выходил 6 вместо 8).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Param, TypeDef
from rptg.plan.route._types import RouteCond, RouteEnvJob, RouteMeasures, RouteSize

if TYPE_CHECKING:
    from rptg._types import Json
    from rptg.plan._types import Ready
    from rptg.plan.route._types import RouteEnvJobs, RouteEnvs


def envs(state: Json, ready: Ready) -> RouteEnvJobs:
    """По готовым элементам, по порядку: у разложения не корня (роль designer) — все операции
    карточки узла, у функции — её операция; прочие не измеряются; окружение — все типы проекта по
    имени, переменные — параметры и result."""
    defs = [TypeDef(name=t["name"], owner=t["owner"], schema=t["schema"], doc=t.get("doc"))
            for _, t in sorted(state["types"].items())]
    out = []
    for r in ready:
        ops = state["cards"][r.node]["ops"] if r.kind == "design" and r.role == "designer" else \
            [o for o in state["cards"][r.node]["ops"] if o["name"] == r.op] if r.kind == "function" else []
        out += [RouteEnvJob(types=defs, vars=[Param(name=p["name"], type=p["type"]) for p in op["params"]]
                            + [Param(name="result", type=op["result"])]) for op in ops]
    return out


def bind(state: Json, ready: Ready, envs: RouteEnvs) -> RouteMeasures:
    """Те же операции в том же порядке: условия requires, затем ensures, и типы параметров, затем
    результат — каждое с окружением своей операции."""
    made, conds, sizes = iter(envs), [], []
    for r in ready:
        ops = state["cards"][r.node]["ops"] if r.kind == "design" and r.role == "designer" else \
            [o for o in state["cards"][r.node]["ops"] if o["name"] == r.op] if r.kind == "function" else []
        for op in ops:
            env = next(made).env
            conds += [RouteCond(text=text, env=env) for text in op["requires"] + op["ensures"]]
            sizes += [RouteSize(type=t, env=env) for t in [p["type"] for p in op["params"]] + [op["result"]]]
    return RouteMeasures(conds=conds, sizes=sizes)
