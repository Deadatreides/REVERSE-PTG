"""Лист rptg.check.graph.tree — инварианты дерева разложения (LOGIC §3, П2).

Функции приняты по карточке design/rptg.check.graph.yaml; обвязку пишет скрипт. Ответ сюда
приходит прошедшим П1, состояние — записью типизированного State: обязательные поля читаются
напрямую. Нарушение — строка «Iн: место: что».
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json, Strings


def check(state: Json, answer: Answer, form: Evidences, cfg: Config) -> Strings:
    """I1 путь и уровень ребёнка, I3 число детей и операций, I8 uses — братья или uses родителя и
    финальность на max_depth, I9 циклы uses между братьями, I11 прогресс (est_lines меньше, чем у
    родителя; интерфейс не повторён; у единственного ребёнка схемы не только вызывают его), I17
    родитель, владелец и владелец типов, I18 эффекты и импорты. Не разложение или П1 не прошла —
    пусто."""
    if answer.kind != "design" or not form or form[0].verdict != "pass":
        return []
    lim, x, value = cfg.limits, answer.node, answer.value
    card = state["cards"].get(x)
    if card is None:
        return [f"I1: {x}: нет карточки узла — разложение не с чем сверять"]
    kids, level = value["children"], x.count(".") + 1
    ids = {c["id"] for c in kids}

    def sig(op):
        return json.dumps([[p["type"] for p in op["params"]], op["result"], op["requires"], op["ensures"]])

    def of_child(c):
        cid, out = c["id"], []
        if not cid.startswith(x + ".") or cid.count(".") != level:
            out.append(f"I1: {cid}: путь не продолжает путь родителя {x}")
        if level + 1 > lim.max_depth:
            out.append(f"I1: {cid}: уровень {level + 1} больше max_depth {lim.max_depth}")
        if c.get("parent") != x or c["owner"] != x:
            out.append(f"I17: {cid}: родитель и владелец обязаны быть {x}")
        if not c["ops"]:
            out.append(f"I3: {cid}: у узла нет операций")
        if c["est_lines"] >= card["est_lines"]:
            out.append(f"I11: {cid}: est_lines {c['est_lines']} не меньше, чем у родителя ({card['est_lines']})")
        if sorted(map(sig, c["ops"])) == sorted(map(sig, card["ops"])):
            out.append(f"I11: {cid}: ребёнок повторяет интерфейс родителя")
        return out + scope(c)

    def scope(c):
        cid, out = c["id"], []
        if not set(c["effects"]) <= set(card["effects"]) or any(not set(o["effects"]) <= set(c["effects"]) for o in c["ops"]):
            out.append(f"I18: {cid}: эффекты шире родительских или шире эффектов узла")
        extra = sorted(set(c["allowed_imports"]) - set(card["allowed_imports"]))
        if extra:
            out.append(f"I18: {cid}: импорты шире родительских: {extra}")
        out += [f"I8: {cid}: uses {u} — не брат и не из uses родителя" for u in c["uses"] if u not in ids | set(card["uses"])]
        if level + 1 == lim.max_depth and (c["uses"] or len(c["ops"]) > lim.final_max_ops):
            out.append(f"I8: {cid}: узел на max_depth обязан уметь быть финальным")
        return out

    def whole():
        out = [f"I3: {x}: детей {len(kids)} больше {lim.max_children}"] if len(kids) > lim.max_children else []
        g = nx.DiGraph()
        g.add_nodes_from(ids)
        g.add_edges_from((c["id"], u) for c in kids for u in c["uses"] if u in ids)
        out += [f"I9: {x}: цикл зависимостей {' → '.join(cycle)}" for cycle in nx.simple_cycles(g)]
        refs = [n.get("call", n.get("map", n.get("fold", ""))) for f in value["flows"].values() for n in f["nodes"]]
        if len(kids) == 1 and all(r.split(":")[0] == kids[0]["id"].rsplit(".", 1)[-1] for r in refs):
            out.append(f"I11: {x}: ребёнок один, а схемы только вызывают его")
        return out

    def owned():
        known = state["types"]
        return [f"I17: тип {t['name']}: владелец {t['owner']}, в проекте — {known.get(t['name'], t)['owner']}; разложение узла {x}"
                for t in value["types"] if t["owner"] != x or known.get(t["name"], t)["owner"] != x]

    def effects():
        pool = {c["id"].rsplit(".", 1)[-1]: c for c in [state["cards"][u] for u in card["uses"]] + kids}
        out = []
        for op in card["ops"]:
            for n in value["flows"].get(op["name"], {"nodes": []})["nodes"]:
                short, _, name = n.get("call", n.get("map", n.get("fold", ""))).partition(":")
                called = {e for o in pool.get(short, {"ops": []})["ops"] if o["name"] == name or not name for e in o["effects"]}
                if called - set(op["effects"]):
                    out.append(f"I18: {x}:{op['name']}: вызывает {short} с эффектами {sorted(called - set(op['effects']))}")
        return out

    return [p for c in kids for p in of_child(c)] + whole() + owned() + effects()
