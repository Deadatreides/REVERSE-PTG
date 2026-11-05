"""Типы, которыми владеет узел rptg.bench.

Сгенерировано tools/codegen0.py по design/rptg.bench.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Cell, Decimal, Sha, Strings, Task, WorkClass



@dataclass(kw_only=True)
class Halves:
    """раздел набора: имена задач подбора и проверки по роду, внутри рода — по возрастанию хэша"""
    fit: Strings
    check: Strings


@dataclass(kw_only=True)
class Tally:
    """клетка до цены: оператор и класс, выборка и успехи на подборе и на проверке, цены итогов клетки, мало данных"""
    operator: str
    class_: WorkClass = field(metadata={"json": 'class'})
    n_fit: int
    ok_fit: int
    n_check: int
    ok_check: int
    costs: Costs
    low_data: bool


Digests = list[Sha]
"""хэши по порядку"""

CalTasks = list[Task]
"""задачи калибровки по порядку"""

Costs = list[Decimal]
"""цены итогов по порядку, десятичные записи"""

Tallies = list[Tally]
"""клетки до цены по порядку класса и оператора"""

Cells = list[Cell]
"""клетки таблицы компетенций по порядку"""


SCHEMAS: dict[str, Any] = {
    'Digests': {'type': 'array', 'items': {'$ref': 'Sha'}},
    'Halves': {'type': 'object', 'required': ['fit', 'check'], 'properties': {'fit': {'$ref': 'Strings'}, 'check': {'$ref': 'Strings'}}},
    'CalTasks': {'type': 'array', 'items': {'$ref': 'Task'}},
    'Costs': {'type': 'array', 'items': {'$ref': 'Decimal'}},
    'Tally': {'type': 'object', 'required': ['operator', 'class', 'n_fit', 'ok_fit', 'n_check', 'ok_check', 'costs', 'low_data'], 'properties': {'operator': {'type': 'string'}, 'class': {'$ref': 'WorkClass'}, 'n_fit': {'type': 'integer', 'minimum': 0}, 'ok_fit': {'type': 'integer', 'minimum': 0}, 'n_check': {'type': 'integer', 'minimum': 0}, 'ok_check': {'type': 'integer', 'minimum': 0}, 'costs': {'$ref': 'Costs'}, 'low_data': {'type': 'boolean'}}},
    'Tallies': {'type': 'array', 'items': {'$ref': 'Tally'}},
    'Cells': {'type': 'array', 'items': {'$ref': 'Cell'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
