"""Типы, которыми владеет узел rptg.check.answer.

Сгенерировано tools/codegen0.py по design/rptg.check.answer.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Cl, ClInfo, TypeEnv



@dataclass(kw_only=True)
class CondJob:
    """задание языку условий: разобрать и типизировать условие в окружении его операции; where — операция, сторона и номер условия"""
    where: str
    text: Cl
    env: TypeEnv


CondJobs = list[CondJob]
"""задания разбора условий"""

ClInfos = list[ClInfo]
"""итоги разбора условий — по одному на задание, в том же порядке"""


SCHEMAS: dict[str, Any] = {
    'CondJob': {'type': 'object', 'required': ['where', 'text', 'env'], 'properties': {'where': {'type': 'string'}, 'text': {'$ref': 'Cl'}, 'env': {'$ref': 'TypeEnv'}}},
    'CondJobs': {'type': 'array', 'items': {'$ref': 'CondJob'}},
    'ClInfos': {'type': 'array', 'items': {'$ref': 'ClInfo'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
