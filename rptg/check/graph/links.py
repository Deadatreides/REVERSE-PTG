"""Лист rptg.check.graph.links — связность схем потоков (LOGIC §2.3, §3: I4–I7).

Функции приняты по карточке design/rptg.check.graph.yaml; обвязку пишет скрипт. Ответ сюда
приходит прошедшим П1, состояние — записью типизированного State: обязательные поля читаются
напрямую. Нарушение — строка «Iн: схема, узел: что».
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json, Strings


def check(state: Json, answer: Answer, form: Evidences) -> Strings:
    """I4 — у каждой операции узла есть схема, у схемы — операция; I5 — узел схемы ровно одного
    вида, ид не повторяются, источник — параметр, выход узла выше или элемент (С-15), имя элемента
    не заслоняет параметр, параметры вызываемого и поля записи питаются ровно своими источниками;
    I6 — выход используется или он результат; I7 — без циклов. Не разложение или П1 не прошла —
    пусто."""
    if answer.kind != "design" or not form or form[0].verdict != "pass":
        return []
    value, card = answer.value, state["cards"][answer.node]
    ops = {o["name"]: o for o in card["ops"]}

    def lookup():
        kids = {c["id"].rsplit(".", 1)[-1]: c for c in [state["cards"][u] for u in card["uses"]] + value["children"]}
        return kids, {n: t["schema"] for n, t in state["types"].items()} | {t["name"]: t["schema"] for t in value["types"]}

    kids, types = lookup()

    def head(s):
        return s.split(".")[0].split("[")[0] if isinstance(s, str) else None

    def wants(n):
        if "record" in n:
            s = types.get(n["record"], {})
            return set(s.get("required", [])), set(s.get("properties", {}))
        short, _, name = n.get("call", n.get("map", n.get("fold", ""))).partition(":")
        want = {p["name"] for o in kids.get(short, {"ops": []})["ops"] if o["name"] == name or not name for p in o["params"]}
        return want, want

    def sources(where, n, known, g, used):
        out = []
        for s in list(n.get("args", n.get("fields", {})).values()) + [n[k] for k in ("over", "init") if k in n]:
            if head(s) in g:
                g.add_edge(head(s), n["id"])
                used.add(head(s))
            elif head(s) not in known | {n.get("item"), None}:
                out.append(f"I5: {where}: источник {s} не найден")
        return out

    def of_node(where, n, known, g, used):
        if sum(k in n for k in ("call", "map", "fold", "record")) != 1:
            return [f"I5: {where}: нужно ровно одно из call, map, fold, record"]
        need, allowed = wants(n)
        fed = set(n.get("args", n.get("fields", {}))) | ({n.get("item")} & need) | ({n.get("acc")} - {None})
        out = [f"I5: {where}: имя элемента {n['item']} совпадает с параметром"] if n.get("item") in known else []
        if not need <= fed or not fed <= allowed:
            out.append(f"I5: {where}: питаются {sorted(fed)}, а нужно {sorted(need)}")
        return out + sources(where, n, known, g, used)

    def ends(name, flow, known, g, used):
        result = head(flow["result"])
        out = [] if result in g or result in known | {None} else [f"I5: схема {name}: результат {flow['result']} не найден"]
        return out + [f"I6: схема {name}: выход {i} не используется" for i in g if i not in used | {result}]

    def of_flow(name, flow):
        ids = [n["id"] for n in flow["nodes"]]
        g, used, known = nx.DiGraph(), set(), {p["name"] for p in ops[name]["params"]}
        g.add_nodes_from(ids)
        out = [f"I5: схема {name}: узел {i} повторяется" for i in sorted(set(ids)) if ids.count(i) > 1]
        out += [p for n in flow["nodes"] for p in of_node(f"схема {name}, узел {n['id']}", n, known, g, used)]
        out += [f"I7: схема {name}: цикл {' → '.join(cycle)}" for cycle in nx.simple_cycles(g)]
        return out + ends(name, flow, known, g, used)

    def missing():
        out = [f"I4: {answer.node}:{name}: нет схемы потока" for name in ops if name not in value["flows"]]
        return out + [f"I4: {answer.node}: схема {name} — у узла нет такой операции" for name in value["flows"] if name not in ops]

    return missing() + [p for name, flow in value["flows"].items() if name in ops for p in of_flow(name, flow)]
