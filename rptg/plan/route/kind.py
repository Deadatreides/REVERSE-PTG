"""Лист rptg.plan.route.kind — вид детей разложения по правилам LOGIC §6.2 и повышению (§7.4).

Функции приняты по карточке design/rptg.plan.route.yaml; обвязку пишет скрипт. «Сначала целиком»:
по умолчанию узел финальный, составным становится по необходимости (F28, LIFE-9, SWE1).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.plan._types import KindDecision

if TYPE_CHECKING:
    from rptg._types import Config, Json, Strings
    from rptg.plan._types import KindDecisions
    from rptg.plan.route._types import Overrides


def children(state: Json, node: str) -> Strings:
    """Дети разложения узла по порядку; пустой узел или узел без разложения — пусто."""
    return [c["id"] for c in state["designs"][node]["children"]] if node in state["designs"] else []


def decide(state: Json, children: Strings, manual: Overrides, cfg: Config) -> KindDecisions:
    """По порядку правил, срабатывает первое: уровень = max_depth — final (2); есть uses — composite
    (3); операций больше final_max_ops — composite (4); функция узла повышена — composite
    (promotion); ручной kind — как назначено (5); est_lines (ручное или из карточки) больше
    final_max_lines × число операций — composite (6); иначе final (7)."""
    lim, out = cfg.limits, []
    for node, m in zip(children, manual):
        card = state["cards"][node]
        promoted = any(e["state"] == "promoted" for s, e in state["elements"].items() if s.startswith(f"function:{node}:"))
        if node.count(".") + 1 >= lim.max_depth:
            kind, rule = "final", "2"
        elif card["uses"]:
            kind, rule = "composite", "3"
        elif len(card["ops"]) > lim.final_max_ops:
            kind, rule = "composite", "4"
        elif promoted:
            kind, rule = "composite", "promotion"
        elif m.kind:
            kind, rule = m.kind, "5"
        elif (m.est_lines or card["est_lines"]) > lim.final_max_lines * len(card["ops"]):
            kind, rule = "composite", "6"
        else:
            kind, rule = "final", "7"
        out.append(KindDecision(node=node, kind=kind, rule=rule))
    return out
