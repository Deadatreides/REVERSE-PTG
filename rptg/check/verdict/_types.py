"""Типы, которыми владеет узел rptg.check.verdict.

Сгенерировано tools/codegen0.py по design/rptg.check.verdict.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Json, Sha
from rptg.check._types import SubjectRef



@dataclass(kw_only=True)
class Applied:
    """состояние с применённым ответом, предмет события и сырой текст неизвлечённого ответа (иначе null)"""
    state: Json
    subject: str
    raw: Json | None = None


@dataclass(kw_only=True)
class Needed:
    """содержимое хэша предмета и предметов, чья приёмка нужна для его приёмки (у сборки — разложение и все дети поддерева)"""
    main: SubjectRef
    more: SubjectRefs


SubjectRefs = list[SubjectRef]
"""предметы с содержимым их хэшей"""

Shas = list[Sha]
"""хэши — по одному на предмет, в том же порядке"""


SCHEMAS: dict[str, Any] = {
    'Applied': {'type': 'object', 'required': ['state', 'subject'], 'properties': {'state': {'$ref': 'Json'}, 'subject': {'type': 'string'}, 'raw': {'$ref': 'Json'}}},
    'SubjectRefs': {'type': 'array', 'items': {'$ref': 'SubjectRef'}},
    'Needed': {'type': 'object', 'required': ['main', 'more'], 'properties': {'main': {'$ref': 'SubjectRef'}, 'more': {'$ref': 'SubjectRefs'}}},
    'Shas': {'type': 'array', 'items': {'$ref': 'Sha'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
