"""Типы, которыми владеет узел rptg.check.

Сгенерировано tools/codegen0.py по design/rptg.check.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Evidences, Json, TypeEnv, Validation



@dataclass(kw_only=True)
class Parts:
    """доказательства по слоям до сборки; неприменимый к событию слой — пустой список"""
    form: Evidences
    structure: Evidences
    data: Evidences
    logic: Evidences
    examples: Evidences
    static: Evidences
    runs: Evidences


@dataclass(kw_only=True)
class SubjectRef:
    """предмет события и содержимое его хэша H(x) по LOGIC §10 — JSON, в котором всё, против чего предмет проверялся"""
    subject: str
    content: Json


@dataclass(kw_only=True)
class ValidateJob:
    """задание языку типов: проверить значение по типу в окружении; where — место для отчёта"""
    where: str
    value: Json
    type: str
    env: TypeEnv


@dataclass(kw_only=True)
class CaseInput:
    """вход контрольного случая для конвейера проверок: состояние и событие в JSON; edges — отдельные рёбра П3 вида {source_type, target_type, env}"""
    state: Json
    event: Json
    edges: Json


ValidateJobs = list[ValidateJob]
"""задания проверки значений по типам"""

Validations = list[Validation]
"""итоги проверки значений по типам — по одному на задание, в том же порядке"""


SCHEMAS: dict[str, Any] = {
    'Parts': {'type': 'object', 'required': ['form', 'structure', 'data', 'logic', 'examples', 'static', 'runs'], 'properties': {'form': {'$ref': 'Evidences'}, 'structure': {'$ref': 'Evidences'}, 'data': {'$ref': 'Evidences'}, 'logic': {'$ref': 'Evidences'}, 'examples': {'$ref': 'Evidences'}, 'static': {'$ref': 'Evidences'}, 'runs': {'$ref': 'Evidences'}}},
    'SubjectRef': {'type': 'object', 'required': ['subject', 'content'], 'properties': {'subject': {'type': 'string'}, 'content': {'$ref': 'Json'}}},
    'ValidateJob': {'type': 'object', 'required': ['where', 'value', 'type', 'env'], 'properties': {'where': {'type': 'string'}, 'value': {'$ref': 'Json'}, 'type': {'type': 'string'}, 'env': {'$ref': 'TypeEnv'}}},
    'ValidateJobs': {'type': 'array', 'items': {'$ref': 'ValidateJob'}},
    'Validations': {'type': 'array', 'items': {'$ref': 'Validation'}},
    'CaseInput': {'type': 'object', 'required': ['state', 'event', 'edges'], 'properties': {'state': {'$ref': 'Json'}, 'event': {'$ref': 'Json'}, 'edges': {'$ref': 'Json'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
