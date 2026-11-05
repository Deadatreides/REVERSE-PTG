"""Типы, которыми владеет узел rptg.plan.machine.

Сгенерировано tools/codegen0.py по design/rptg.plan.machine.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Acceptance, Event, Evidences, Json, Report, Subject



@dataclass(kw_only=True)
class RecheckTargets:
    """что перепроверять: состояние с устаревшими элементами, предметы и их значения по порядку"""
    state: Json
    subjects: Subjects
    values: RecheckValues


@dataclass(kw_only=True)
class RecheckJobs:
    """перепроверка: состояние, события и их предметы по порядку"""
    state: Json
    events: RecheckEvents
    subjects: Subjects


@dataclass(kw_only=True)
class RecheckStored:
    """доказательства перепроверки записаны: состояние, провалы по порядку, предметы"""
    state: Json
    failures: RecheckValues
    subjects: Subjects


Subjects = list[Subject]
"""предметы по порядку"""

RecheckValues = list[Json]
"""значения предметов перепроверки: разложение без node, у функции — пустой объект"""

RecheckEvents = list[Event]
"""события перепроверки без модели: сохранённое разложение или код как ответ, расход нулевой"""

EvidenceSets = list[Evidences]
"""доказательства по событиям перепроверки, в порядке событий"""

Acceptances = list[Acceptance]
"""приёмка предметов перепроверки по порядку"""

Reports = list[Report]
"""отчёты о провалах по порядку провалов"""


SCHEMAS: dict[str, Any] = {
    'Subjects': {'type': 'array', 'items': {'$ref': 'Subject'}},
    'RecheckValues': {'type': 'array', 'items': {'$ref': 'Json'}},
    'RecheckTargets': {'type': 'object', 'required': ['state', 'subjects', 'values'], 'properties': {'state': {'$ref': 'Json'}, 'subjects': {'$ref': 'Subjects'}, 'values': {'$ref': 'RecheckValues'}}},
    'RecheckEvents': {'type': 'array', 'items': {'$ref': 'Event'}},
    'EvidenceSets': {'type': 'array', 'items': {'$ref': 'Evidences'}},
    'RecheckJobs': {'type': 'object', 'required': ['state', 'events', 'subjects'], 'properties': {'state': {'$ref': 'Json'}, 'events': {'$ref': 'RecheckEvents'}, 'subjects': {'$ref': 'Subjects'}}},
    'RecheckStored': {'type': 'object', 'required': ['state', 'failures', 'subjects'], 'properties': {'state': {'$ref': 'Json'}, 'failures': {'$ref': 'RecheckValues'}, 'subjects': {'$ref': 'Subjects'}}},
    'Acceptances': {'type': 'array', 'items': {'$ref': 'Acceptance'}},
    'Reports': {'type': 'array', 'items': {'$ref': 'Report'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
