"""Типы, которыми владеет узел rptg.views.

Сгенерировано tools/codegen0.py по design/rptg.views.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Acceptance, Subject



NodeSubjects = list[Subject]
"""предметы элементов узла по порядку"""

NodeAcceptances = list[Acceptance]
"""приёмка элементов узла по порядку их предметов"""


SCHEMAS: dict[str, Any] = {
    'NodeSubjects': {'type': 'array', 'items': {'$ref': 'Subject'}},
    'NodeAcceptances': {'type': 'array', 'items': {'$ref': 'Acceptance'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
