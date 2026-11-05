"""Лист rptg.talk.schema — схема ответа задачи (LOGIC §8.3, experiment14).

Функции приняты по карточке design/rptg.talk.yaml; обвязку пишет скрипт. Схема — та же, по которой
П1 проверяет ответ (check.answer.shape): записи закрыты, непрозрачный Json открыт. Отличие одно —
запись ссылок: у ядра {$ref: Имя}, у поставщиков и в тексте подсказки {$ref: #/$defs/Имя}, иначе
её не примут ни структурный вывод, ни перевод схемы в грамматику llama.cpp.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import SCHEMAS

if TYPE_CHECKING:
    from rptg._types import Json, Task


def answer(task: Task) -> Json:
    """Карта — MapAnswer, разложение, ревизия и шаги split — Design, функция — null. Замыкание типов по
    ссылкам; запись с properties получает additionalProperties: false, если его нет; сам тип — вверху,
    остальные — в $defs по имени."""
    root = {"map": "MapAnswer", "function": None}.get(task.kind, "Design")
    if root is None:
        return None

    def convert(schema, found):
        if isinstance(schema, list):
            return [convert(v, found) for v in schema]
        if not isinstance(schema, dict):
            return schema
        out = {k: convert(v, found) for k, v in schema.items()}
        if isinstance(schema.get("$ref"), str):
            found.append(schema["$ref"])
            out["$ref"] = "#/$defs/" + schema["$ref"]
        if isinstance(schema.get("properties"), dict):
            out.setdefault("additionalProperties", False)
        return out

    defs: dict = {}
    todo = [root]
    while todo:
        name = todo.pop()
        if name not in defs:
            found: list = []
            defs[name] = convert(SCHEMAS[name], found)
            todo += found
    top = defs.pop(root)
    return {**top, "$defs": dict(sorted(defs.items()))}
