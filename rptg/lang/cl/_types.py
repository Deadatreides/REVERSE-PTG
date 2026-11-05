"""Типы, которыми владеет узел rptg.lang.cl.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Json, StrMap, Strings



@dataclass(kw_only=True)
class ClAst:
    """дерево разбора CL в JSON: k — вид узла; op — оператор; name — имя пути, функции или переменной квантора; v — значение литерала; args — дети; steps — шаги пути"""
    k: str
    op: str | None = None
    name: str | None = None
    v: Json | None = None
    args: list[ClAst] | None = None
    steps: list[ClStep] | None = None


@dataclass(kw_only=True)
class ClStep:
    """шаг пути: поле или индекс"""
    attr: str | None = None
    idx: ClAst | None = None


@dataclass(kw_only=True)
class ParseResult:
    """итог разбора; ошибки — с позицией в тексте"""
    ok: bool
    errors: Strings
    ast: ClAst | None = None


@dataclass(kw_only=True)
class Typed:
    """типизированное условие; paths — вид каждого пути (связанная переменная квантора заменена путём списка с []): integer, number, decimal, string, boolean, enum:A,B, list, record, dict, json, с приставкой opt: у необязательных"""
    ok: bool
    errors: Strings
    type: str
    ast: ClAst | None = None
    paths: StrMap


@dataclass(kw_only=True)
class ClMeasures:
    """меры условия (LOGIC §4.5)"""
    nodes: int
    quant: int
    nonlin: int
    arith: bool
    strings: bool
    names: Strings


ParseResults = list[ParseResult]
"""итоги разбора списка условий"""

Typeds = list[Typed]
"""список типизированных условий"""


SCHEMAS: dict[str, Any] = {
    'ClAst': {'type': 'object', 'required': ['k'], 'properties': {'k': {'type': 'string', 'enum': ['impl', 'or', 'and', 'not', 'cmp', 'in', 'arith', 'neg', 'num', 'str', 'bool', 'null', 'path', 'func', 'quant', 'agg', 'set']}, 'op': {'type': 'string'}, 'name': {'type': 'string'}, 'v': {'$ref': 'Json'}, 'args': {'type': 'array', 'items': {'$ref': 'ClAst'}}, 'steps': {'type': 'array', 'items': {'$ref': 'ClStep'}}}},
    'ClStep': {'type': 'object', 'properties': {'attr': {'type': 'string'}, 'idx': {'$ref': 'ClAst'}}},
    'ParseResult': {'type': 'object', 'required': ['ok', 'errors'], 'properties': {'ok': {'type': 'boolean'}, 'errors': {'$ref': 'Strings'}, 'ast': {'$ref': 'ClAst'}}},
    'ParseResults': {'type': 'array', 'items': {'$ref': 'ParseResult'}},
    'Typed': {'type': 'object', 'required': ['ok', 'errors', 'type', 'paths'], 'properties': {'ok': {'type': 'boolean'}, 'errors': {'$ref': 'Strings'}, 'type': {'type': 'string'}, 'ast': {'$ref': 'ClAst'}, 'paths': {'$ref': 'StrMap'}}},
    'Typeds': {'type': 'array', 'items': {'$ref': 'Typed'}},
    'ClMeasures': {'type': 'object', 'required': ['nodes', 'quant', 'nonlin', 'arith', 'strings', 'names'], 'properties': {'nodes': {'type': 'integer', 'minimum': 0}, 'quant': {'type': 'integer', 'minimum': 0}, 'nonlin': {'type': 'integer', 'minimum': 0}, 'arith': {'type': 'boolean'}, 'strings': {'type': 'boolean'}, 'names': {'$ref': 'Strings'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
