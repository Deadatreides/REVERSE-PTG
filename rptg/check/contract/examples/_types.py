"""Типы, которыми владеет узел rptg.check.contract.examples.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.examples.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Cl, EvalResult, Json, Strings, TypeEnv
from rptg.check._types import ValidateJobs



@dataclass(kw_only=True)
class EvalJob:
    """задание языку условий: значение условия на данных примера"""
    where: str
    text: Cl
    env: TypeEnv
    values: Json


@dataclass(kw_only=True)
class SampleJobs:
    """задания П7: значения примеров по типам, условия на примерах, нарушения, видимые без языка (I15, вход не по параметрам, «*» в точном примере)"""
    applicable: bool
    subject: str
    validations: ValidateJobs
    evals: EvalJobs
    problems: Strings


EvalJobs = list[EvalJob]
"""задания вычисления условий"""

EvalResults = list[EvalResult]
"""итоги вычисления условий — по одному на задание, в том же порядке"""


SCHEMAS: dict[str, Any] = {
    'EvalJob': {'type': 'object', 'required': ['where', 'text', 'env', 'values'], 'properties': {'where': {'type': 'string'}, 'text': {'$ref': 'Cl'}, 'env': {'$ref': 'TypeEnv'}, 'values': {'$ref': 'Json'}}},
    'EvalJobs': {'type': 'array', 'items': {'$ref': 'EvalJob'}},
    'EvalResults': {'type': 'array', 'items': {'$ref': 'EvalResult'}},
    'SampleJobs': {'type': 'object', 'required': ['applicable', 'subject', 'validations', 'evals', 'problems'], 'properties': {'applicable': {'type': 'boolean'}, 'subject': {'type': 'string'}, 'validations': {'$ref': 'ValidateJobs'}, 'evals': {'$ref': 'EvalJobs'}, 'problems': {'$ref': 'Strings'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
