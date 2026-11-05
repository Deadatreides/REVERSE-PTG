"""Лист rptg.views.graph — граф сети для окна: узлы с видом и меткой назначения, рёбра, цвет узла
(ARCHITECTURE §7: серый — запланирован, жёлтый — в работе, зелёный — принят, красный — отказ,
фиолетовый — подозрение на карточку).

Функции приняты по карточке design/rptg.views.yaml; обвязку пишет скрипт. Структура и цвет — две работы,
две операции (после Э1 04.10.2026: в одной функции решений было 26 при допуске 21,5). «Отказ» — элемент
ждёт пользователя: остановка, которой нужен ответ. Принят составной узел, когда принята его сборка,
финальный — когда приняты все функции: принятое разложение ещё не значит, что узел собран.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json


def build(state: Json) -> Json:
    """Узлы — карточки по порядку id: родитель (у корня пусто); вид — составной (есть разложение или его
    элемент), финальный (есть элементы функций), иначе pending; оператор и источник — назначения
    разложения у составного, первой функции у финального (нет — пусто). Рёбра — child от родителя по
    порядку узлов, затем uses от узла к используемому."""
    els, cards = state["elements"], state["cards"]

    def kind(node, mine):
        if node in state["designs"] or f"design:{node}" in mine:
            return "composite"
        return "final" if any(k.startswith("function:") for k in mine) else "pending"

    def item(node):
        mine = {k: e for k, e in els.items() if k.split(":")[1] == node}
        sort = kind(node, mine)
        key = f"design:{node}" if sort == "composite" else next((k for k in sorted(mine) if k.startswith("function:")), "")
        a = mine.get(key, {}).get("assignment") or {}
        return {"id": node, "parent": cards[node].get("parent") or "", "kind": sort, "operator": a.get("operator", ""),
                "decided_by": a.get("decided_by", "")}

    edges = [{"from": cards[n]["parent"], "to": n, "kind": "child"} for n in sorted(cards) if cards[n].get("parent")]
    edges += [{"from": n, "to": u, "kind": "uses"} for n in sorted(cards) for u in cards[n]["uses"]]
    return {"nodes": [item(n) for n in sorted(cards)], "edges": edges}


def paint(state: Json, graph: Json) -> Json:
    """Цвет узла по его элементам: suspect — элемент под подозрением; failed — элемент ждёт пользователя;
    accepted — у составного принята сборка, у финального есть функции и все приняты; working — элемент
    сдвинулся с planned; иначе planned. Узлы — с полем status, рёбра — как есть."""
    def done(n, mine):
        funcs = [e["state"] for k, e in mine.items() if k.startswith("function:")]
        if n["kind"] == "composite":
            return mine.get(f"assembly:{n['id']}", {}).get("state") == "accepted"
        return bool(funcs) and set(funcs) == {"accepted"}

    def status(n):
        mine = {k: e for k, e in state["elements"].items() if k.split(":")[1] == n["id"]}
        states = [e["state"] for e in mine.values()]
        hits = [("suspect", "card_suspect" in states), ("failed", any((e.get("policy_path") or "").startswith("user:") for e in mine.values())),
                ("accepted", done(n, mine)), ("working", any(s != "planned" for s in states))]
        return next((name for name, hit in hits if hit), "planned")

    return {"nodes": [{**n, "status": status(n)} for n in graph["nodes"]], "edges": list(graph["edges"])}
