"""Типы, которыми владеет узел rptg.lang.cl.logic.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.logic.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import StrMap, Strings



@dataclass(kw_only=True)
class SmtTerm:
    """одно условие в SMT-LIB: формула, сорт каждого символа (символ — путь CL, в тексте в кавычках |…|), неявные факты типов, виды путей условия"""
    ok: bool
    errors: Strings
    term: str
    sorts: StrMap
    facts: Strings
    paths: StrMap


@dataclass(kw_only=True)
class SmtText:
    """текст задачи SMT-LIB и что нужно для расшифровки: сорта символов, символы цели"""
    ok: bool
    errors: Strings
    text: str
    kinds: StrMap
    goal_symbols: Strings
    bound: int


@dataclass(kw_only=True)
class SolveResult:
    """ответ решателя: модель — символ → значение текстом; ядро — имена противоречивых утверждений"""
    status: str
    model: StrMap
    core: Strings
    reason: str | None = None


SmtTerms = list[SmtTerm]
"""формулы списка условий"""


SCHEMAS: dict[str, Any] = {
    'SmtTerm': {'type': 'object', 'required': ['ok', 'errors', 'term', 'sorts', 'facts', 'paths'], 'properties': {'ok': {'type': 'boolean'}, 'errors': {'$ref': 'Strings'}, 'term': {'type': 'string'}, 'sorts': {'$ref': 'StrMap'}, 'facts': {'$ref': 'Strings'}, 'paths': {'$ref': 'StrMap'}}},
    'SmtTerms': {'type': 'array', 'items': {'$ref': 'SmtTerm'}},
    'SmtText': {'type': 'object', 'required': ['ok', 'errors', 'text', 'kinds', 'goal_symbols', 'bound'], 'properties': {'ok': {'type': 'boolean'}, 'errors': {'$ref': 'Strings'}, 'text': {'type': 'string'}, 'kinds': {'$ref': 'StrMap'}, 'goal_symbols': {'$ref': 'Strings'}, 'bound': {'type': 'integer', 'minimum': 1}}},
    'SolveResult': {'type': 'object', 'required': ['status', 'model', 'core'], 'properties': {'status': {'type': 'string', 'enum': ['sat', 'unsat', 'unknown']}, 'model': {'$ref': 'StrMap'}, 'core': {'$ref': 'Strings'}, 'reason': {'type': 'string'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
