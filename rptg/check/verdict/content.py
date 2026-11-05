"""Лист rptg.check.verdict.content — содержимое хэша H(x) по LOGIC §10.

Функции приняты по карточке design/rptg.check.verdict.yaml; обвязку пишет скрипт. Правило одно
для всех H: в хэш входит всё, против чего предмет проверялся. Вложенное содержимое вместо хэшей
детей равносильно им: меняется ребёнок — меняется и содержимое сборки. Состояние — запись
типизированного State, обязательные поля читаются напрямую.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.check._types import SubjectRef
from rptg.check.verdict._types import Needed

if TYPE_CHECKING:
    from rptg._types import Json


def of(state: Json, subject: str, raw: Json) -> Needed:
    """raw не null — содержимое сам raw. Разложение X — само разложение, карточка X, карточки uses X,
    типы строгих предков X (свои типы X лежат в разложении). Функция — код, операция без имени,
    используемые типы по ссылкам, импорты и эффекты узла. Сборка X — разложение X и содержимое
    детей; в more — разложение X и все предметы поддерева, чья приёмка нужна. Карта — ответ карты и
    примеры пользователя. Неизвестный предмет — пустой объект."""
    more: list = []

    def refs(s):
        if isinstance(s, dict):
            return [v for k, v in s.items() if k == "$ref"] + [r for v in s.values() for r in refs(v)]
        return [r for v in s for r in refs(v)] if isinstance(s, list) else []

    def design_of(node, _=""):
        parts, card = node.split("."), state["cards"][node]
        owners = {".".join(parts[:i]) for i in range(1, len(parts))}
        return {"design": state["designs"].get(node), "card": card,
                "uses": {u: state["cards"][u] for u in sorted(card["uses"])},
                "types": {n: t for n, t in sorted(state["types"].items()) if t["owner"] in owners}}

    def function_of(node, name):
        card = state["cards"][node]
        op = next(o for o in card["ops"] if o["name"] == name)
        used: dict = {}
        todo = [p["type"] for p in op["params"]] + [op["result"]]
        while todo:
            t = todo.pop().strip("[]")
            if t in state["types"] and t not in used:
                used[t] = state["types"][t]
                todo += refs(used[t]["schema"])
        return {"code": state["code"].get(f"{node}:{name}"), "op": {k: v for k, v in op.items() if k != "name"},
                "types": dict(sorted(used.items())), "imports": card["allowed_imports"], "effects": card["effects"]}

    def child_of(cid):
        if cid in state["designs"]:
            more.append(SubjectRef(subject=f"assembly:{cid}", content=assembly_of(cid)))
            return more[-1].content
        ops = {op["name"]: function_of(cid, op["name"]) for op in state["cards"][cid]["ops"]}
        more.extend(SubjectRef(subject=f"function:{cid}:{name}", content=f) for name, f in ops.items())
        return ops

    def assembly_of(node, _=""):
        more.append(SubjectRef(subject=f"design:{node}", content=design_of(node)))
        return {"design": more[-1].content, "children": {c["id"]: child_of(c["id"]) for c in state["designs"][node]["children"]}}

    def map_of(node, _=""):
        return {"map": {"map_text": state["map_text"], "card": state["cards"].get(node),
                        "types": [t for _, t in sorted(state["types"].items()) if t["owner"] == node]},
                "user_examples": state["user_examples"]}

    if raw is not None:
        return Needed(main=SubjectRef(subject=subject, content=raw), more=[])
    kind, _, rest = subject.partition(":")
    node, _, name = rest.partition(":")
    build = {"design": design_of, "function": function_of, "assembly": assembly_of, "map": map_of}.get(kind)
    return Needed(main=SubjectRef(subject=subject, content=build(node, name) if build else {}), more=more)
