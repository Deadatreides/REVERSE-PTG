"""Типы, которыми владеет узел rptg.plan.route.

Сгенерировано tools/codegen0.py по design/rptg.plan.route.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Cl, ClInfo, EnvResult, Override, Params, TypeDefs, TypeEnv



@dataclass(kw_only=True)
class RouteEnvJob:
    """задание окружения операции для lang:type_env — все типы проекта и переменные операции: параметры и result"""
    types: TypeDefs
    vars: Params


@dataclass(kw_only=True)
class RouteCond:
    """условие операции в её окружении — задание lang:cl_info"""
    text: Cl
    env: TypeEnv


@dataclass(kw_only=True)
class RouteSize:
    """тип параметра или результата в окружении операции — задание lang:type_size"""
    type: str
    env: TypeEnv


@dataclass(kw_only=True)
class RouteMeasures:
    """задания мер: условия и типы измеряемых операций в одном порядке"""
    conds: RouteConds
    sizes: RouteSizes


RouteEnvJobs = list[RouteEnvJob]
"""окружения измеряемых операций: разложения не корня — все операции карточки, функции — своя; по порядку готовых элементов"""

RouteEnvs = list[EnvResult]
"""построенные окружения в порядке заданий"""

RouteConds = list[RouteCond]
"""условия измеряемых операций: requires, затем ensures"""

RouteSizes = list[RouteSize]
"""типы измеряемых операций: параметры, затем результат"""

RouteInfos = list[ClInfo]
"""меры условий в порядке заданий"""

RouteCounts = list[int]
"""размеры типов в порядке заданий"""

Overrides = list[Override]
"""ручные назначения по порядку предметов"""


SCHEMAS: dict[str, Any] = {
    'RouteEnvJob': {'type': 'object', 'required': ['types', 'vars'], 'properties': {'types': {'$ref': 'TypeDefs'}, 'vars': {'$ref': 'Params'}}},
    'RouteEnvJobs': {'type': 'array', 'items': {'$ref': 'RouteEnvJob'}},
    'RouteEnvs': {'type': 'array', 'items': {'$ref': 'EnvResult'}},
    'RouteCond': {'type': 'object', 'required': ['text', 'env'], 'properties': {'text': {'$ref': 'Cl'}, 'env': {'$ref': 'TypeEnv'}}},
    'RouteConds': {'type': 'array', 'items': {'$ref': 'RouteCond'}},
    'RouteSize': {'type': 'object', 'required': ['type', 'env'], 'properties': {'type': {'type': 'string'}, 'env': {'$ref': 'TypeEnv'}}},
    'RouteSizes': {'type': 'array', 'items': {'$ref': 'RouteSize'}},
    'RouteMeasures': {'type': 'object', 'required': ['conds', 'sizes'], 'properties': {'conds': {'$ref': 'RouteConds'}, 'sizes': {'$ref': 'RouteSizes'}}},
    'RouteInfos': {'type': 'array', 'items': {'$ref': 'ClInfo'}},
    'RouteCounts': {'type': 'array', 'items': {'type': 'integer'}},
    'Overrides': {'type': 'array', 'items': {'$ref': 'Override'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
