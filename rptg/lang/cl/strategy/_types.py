"""Типы, которыми владеет узел rptg.lang.cl.strategy.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.strategy.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any



@dataclass(kw_only=True)
class Bound:
    """граница места: name — путь (параметр, поля через точку, элемент списка — []); value — само значение, size — его len; min и max включительно"""
    name: str
    what: str
    side: str
    v: int


Bounds = list[Bound]
"""границы мест: у каждой тройки (путь, что, сторона) — самая тесная"""


SCHEMAS: dict[str, Any] = {
    'Bound': {'type': 'object', 'required': ['name', 'what', 'side', 'v'], 'properties': {'name': {'type': 'string'}, 'what': {'type': 'string', 'enum': ['value', 'size']}, 'side': {'type': 'string', 'enum': ['min', 'max']}, 'v': {'type': 'integer'}}},
    'Bounds': {'type': 'array', 'items': {'$ref': 'Bound'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
