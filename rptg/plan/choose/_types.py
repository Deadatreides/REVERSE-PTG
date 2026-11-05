"""Типы, которыми владеет узел rptg.plan.choose.

Сгенерировано tools/codegen0.py по design/rptg.plan.choose.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Assignments, BuildTarget, Json



@dataclass(kw_only=True)
class Choice:
    """выбор до сборки действия: act — stop, pause, approve (вопрос утверждения), ask (решение или перепроверка), sandbox, model; предмет и роль; причина паузы; вопрос; цель и прогон песочницы; назначение кандидата (одно или пусто); разложение, чей дайджест нужен вопросу утверждения"""
    act: str
    subject: str
    role: str
    reason: str
    question: Json
    target: BuildTarget | None = None
    run: str
    assignments: Assignments
    design: Json



SCHEMAS: dict[str, Any] = {
    'Choice': {'type': 'object', 'required': ['act', 'subject', 'role', 'reason', 'question', 'run', 'assignments', 'design'], 'properties': {'act': {'type': 'string', 'enum': ['stop', 'pause', 'approve', 'ask', 'sandbox', 'model']}, 'subject': {'type': 'string'}, 'role': {'type': 'string'}, 'reason': {'type': 'string'}, 'question': {'$ref': 'Json'}, 'target': {'$ref': 'BuildTarget'}, 'run': {'type': 'string'}, 'assignments': {'$ref': 'Assignments'}, 'design': {'$ref': 'Json'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
