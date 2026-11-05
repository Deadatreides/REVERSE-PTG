"""Типы, которыми владеет узел rptg.check.contract.logic.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.logic.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Cl, Cls, Json, Proof, Sat, StrMap, Strings, TypeEnv



@dataclass(kw_only=True)
class Step:
    """шаг плана П4: fact — факт выше по потоку, goal — обязательство (I13), refine — цель П5, eq — равенство двух значений по их типу (details: left, right, schema), его раскрывает лист equal; text — условие вызываемого, subst — его параметры → выражения CL, guard — условие шага отображения или свёртки (пусто — безусловно)"""
    kind: str
    text: Cl
    subst: StrMap
    guard: str
    details: Json


@dataclass(kw_only=True)
class OpPlan:
    """план П4 одной операции узла: окружение (параметры, выходы узлов схемы, накопители свёрток), шаги по порядку, головы путей, которые остаются в контрпримере"""
    op: str
    env: TypeEnv
    steps: list[Step]
    keep: Strings


@dataclass(kw_only=True)
class SatJob:
    """задание языку условий: выполним ли набор условий (I14)"""
    details: Json
    conds: Cls
    env: TypeEnv


@dataclass(kw_only=True)
class FactPlan:
    """план П4: по операции узла; unknown — чего план не выразил (вердикт unknown, не fail); partial — пути, чьи факты неполны (необязательное поле, словарь, составной литерал): опровержение с контрпримером по такому пути может быть ложным и даёт unknown; p5 — считать ли П5"""
    applicable: bool
    subject: str
    p5: bool
    ops: list[OpPlan]
    unknown: Strings
    partial: Strings


@dataclass(kw_only=True)
class ProofJob:
    """задание языку условий: факты влекут цель; keep — головы путей параметров операции для контрпримера"""
    details: Json
    facts: Cls
    goal: Cl
    env: TypeEnv
    keep: Strings


@dataclass(kw_only=True)
class Obligations:
    """задания решателю по плану П4: обязательства и цели П5; unknown, partial и p5 — из плана"""
    applicable: bool
    subject: str
    p5: bool
    proofs: ProofJobs
    refines: ProofJobs
    unknown: Strings
    partial: Strings


SatJobs = list[SatJob]
"""задания выполнимости"""

ProofJobs = list[ProofJob]
"""задания доказательства"""

Proofs = list[Proof]
"""итоги доказательств — по одному на задание, в том же порядке"""

Sats = list[Sat]
"""итоги выполнимости — по одному на задание, в том же порядке"""


SCHEMAS: dict[str, Any] = {
    'Step': {'type': 'object', 'required': ['kind', 'text', 'subst', 'guard', 'details'], 'properties': {'kind': {'type': 'string', 'enum': ['fact', 'goal', 'refine', 'eq']}, 'text': {'$ref': 'Cl'}, 'subst': {'$ref': 'StrMap'}, 'guard': {'type': 'string'}, 'details': {'$ref': 'Json'}}},
    'OpPlan': {'type': 'object', 'required': ['op', 'env', 'steps', 'keep'], 'properties': {'op': {'type': 'string'}, 'env': {'$ref': 'TypeEnv'}, 'steps': {'type': 'array', 'items': {'$ref': 'Step'}}, 'keep': {'$ref': 'Strings'}}},
    'SatJob': {'type': 'object', 'required': ['details', 'conds', 'env'], 'properties': {'details': {'$ref': 'Json'}, 'conds': {'$ref': 'Cls'}, 'env': {'$ref': 'TypeEnv'}}},
    'SatJobs': {'type': 'array', 'items': {'$ref': 'SatJob'}},
    'FactPlan': {'type': 'object', 'required': ['applicable', 'subject', 'p5', 'ops', 'unknown', 'partial'], 'properties': {'applicable': {'type': 'boolean'}, 'subject': {'type': 'string'}, 'p5': {'type': 'boolean'}, 'ops': {'type': 'array', 'items': {'$ref': 'OpPlan'}}, 'unknown': {'$ref': 'Strings'}, 'partial': {'$ref': 'Strings'}}},
    'ProofJob': {'type': 'object', 'required': ['details', 'facts', 'goal', 'env', 'keep'], 'properties': {'details': {'$ref': 'Json'}, 'facts': {'$ref': 'Cls'}, 'goal': {'$ref': 'Cl'}, 'env': {'$ref': 'TypeEnv'}, 'keep': {'$ref': 'Strings'}}},
    'ProofJobs': {'type': 'array', 'items': {'$ref': 'ProofJob'}},
    'Obligations': {'type': 'object', 'required': ['applicable', 'subject', 'p5', 'proofs', 'refines', 'unknown', 'partial'], 'properties': {'applicable': {'type': 'boolean'}, 'subject': {'type': 'string'}, 'p5': {'type': 'boolean'}, 'proofs': {'$ref': 'ProofJobs'}, 'refines': {'$ref': 'ProofJobs'}, 'unknown': {'$ref': 'Strings'}, 'partial': {'$ref': 'Strings'}}},
    'Proofs': {'type': 'array', 'items': {'$ref': 'Proof'}},
    'Sats': {'type': 'array', 'items': {'$ref': 'Sat'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
