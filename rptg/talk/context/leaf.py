"""Лист rptg.talk.context.leaf — факты задачи функции (LOGIC §8.1, задача «Ф функция»).

Функции приняты по карточке design/rptg.talk.context.yaml; обвязку пишет скрипт. Исполнитель не
видит дерева: только карточку своей операции, назначение узла, классы типов, которые она трогает,
разрешённые импорты и эффекты и пределы Э1.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.talk._types import Fact, Facts

if TYPE_CHECKING:
    from rptg._types import Json, Task


def facts(task: Task, state: Json, cfg: Json) -> Facts:
    """Функция — op (карточка операции с примерами), purpose, types (типы проекта из параметров и
    результата, [T] — тип T, с замыканием по $ref, по имени), imports, limits (max_complexity и
    договор Э1 операции, если объявлен); другой вид — пусто."""
    if task.kind != "function":
        return Facts(sections=[])
    node, name = task.subject.split(":")[1:3]
    card, known = state["cards"][node], state["types"]
    op = next(o for o in card["ops"] if o["name"] == name)

    def refs(schema):
        if isinstance(schema, list):
            return [r for v in schema for r in refs(v)]
        if not isinstance(schema, dict):
            return []
        found = [r for v in schema.values() for r in refs(v)]
        return [schema["$ref"], *found] if "$ref" in schema else found

    todo, seen = [p["type"].strip("[]") for p in op["params"]] + [op["result"].strip("[]")], set()
    while todo:
        n = todo.pop()
        if n in known and n not in seen:
            seen.add(n)
            todo += refs(known[n]["schema"])
    contract = cfg.get("contracts", {}).get(f"{node}:{name}", {})
    return Facts(sections=[
        Fact(key="op", value=op),
        Fact(key="purpose", value=card["purpose"]),
        Fact(key="types", value=[known[n] for n in sorted(seen)]),
        Fact(key="imports", value={"allowed_imports": card["allowed_imports"], "effects": card["effects"]}),
        Fact(key="limits", value={"max_complexity": cfg["limits"]["max_complexity"], **contract}),
    ])
