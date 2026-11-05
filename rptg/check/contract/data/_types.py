"""Типы, которыми владеет узел rptg.check.contract.data.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.data.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import PathType, SubResult, TypeEnv
from rptg.check._types import ValidateJobs



@dataclass(kw_only=True)
class PathJob:
    """задание языку типов: тип значения по пути от корневого типа"""
    root: str
    path: str
    env: TypeEnv


@dataclass(kw_only=True)
class EdgeJob:
    """ребро схемы для П3: тип источника — имя a или итог пути paths[a_at], тип назначения — имя b или итог пути paths[b_at]; номер −1 — имени достаточно"""
    where: str
    a: str
    a_at: int
    b: str
    b_at: int


@dataclass(kw_only=True)
class SubJob:
    """задание языку типов: тип a — подтип b в окружении"""
    where: str
    a: str
    b: str
    env: TypeEnv


@dataclass(kw_only=True)
class EdgeJobs:
    """задания П3: рёбра схем, пути к разрешению, окружение видимых типов, прямые рёбра контрольных случаев, литералы для проверки по типу места; applicable — есть что проверять"""
    applicable: bool
    subject: str
    edges: list[EdgeJob]
    paths: PathJobs
    env: TypeEnv
    direct: SubJobs
    consts: ValidateJobs


PathJobs = list[PathJob]
"""задания разрешения путей"""

PathTypes = list[PathType]
"""итоги разрешения путей — по одному на задание, в том же порядке"""

SubJobs = list[SubJob]
"""задания подтипа"""

SubResults = list[SubResult]
"""итоги подтипа — по одному на задание, в том же порядке"""


SCHEMAS: dict[str, Any] = {
    'PathJob': {'type': 'object', 'required': ['root', 'path', 'env'], 'properties': {'root': {'type': 'string'}, 'path': {'type': 'string'}, 'env': {'$ref': 'TypeEnv'}}},
    'PathJobs': {'type': 'array', 'items': {'$ref': 'PathJob'}},
    'PathTypes': {'type': 'array', 'items': {'$ref': 'PathType'}},
    'EdgeJob': {'type': 'object', 'required': ['where', 'a', 'a_at', 'b', 'b_at'], 'properties': {'where': {'type': 'string'}, 'a': {'type': 'string'}, 'a_at': {'type': 'integer', 'minimum': -1}, 'b': {'type': 'string'}, 'b_at': {'type': 'integer', 'minimum': -1}}},
    'SubJob': {'type': 'object', 'required': ['where', 'a', 'b', 'env'], 'properties': {'where': {'type': 'string'}, 'a': {'type': 'string'}, 'b': {'type': 'string'}, 'env': {'$ref': 'TypeEnv'}}},
    'SubJobs': {'type': 'array', 'items': {'$ref': 'SubJob'}},
    'SubResults': {'type': 'array', 'items': {'$ref': 'SubResult'}},
    'EdgeJobs': {'type': 'object', 'required': ['applicable', 'subject', 'edges', 'paths', 'env', 'direct', 'consts'], 'properties': {'applicable': {'type': 'boolean'}, 'subject': {'type': 'string'}, 'edges': {'type': 'array', 'items': {'$ref': 'EdgeJob'}}, 'paths': {'$ref': 'PathJobs'}, 'env': {'$ref': 'TypeEnv'}, 'direct': {'$ref': 'SubJobs'}, 'consts': {'$ref': 'ValidateJobs'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
