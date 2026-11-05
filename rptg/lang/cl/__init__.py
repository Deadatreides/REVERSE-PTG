"""язык условий CL: разбор, типизация, меры, вычисление, перевод в Python, доказательство, выполнимость, стратегии Hypothesis

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Cl, ClInfo, Cls, EvalResult, Json, Limits, Params, Proof, Sat, StrMap, TypeEnv



def info(text: Cl, env: TypeEnv) -> ClInfo:
    """разбор, типизация и меры условия"""
    result = _flows.info(text=text, env=env)
    _c.check('rptg.lang.cl:info', 'ensures', [
        ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
        ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
    ])
    return result


def eval(text: Cl, env: TypeEnv, values: Json) -> EvalResult:
    """значение условия на данных; деление на ноль даёт ложь"""
    result = _flows.eval(text=text, env=env, values=values)
    _c.check('rptg.lang.cl:eval', 'ensures', [
        ('result.ok => result.error == null', lambda: ((not result.ok) or (result.error is None))),
    ])
    return result


def python(text: Cl, env: TypeEnv) -> str:
    """условие → выражение Python"""
    result = _flows.python(text=text, env=env)
    _c.check('rptg.lang.cl:python', 'ensures', [
        ('len(result) >= 1', lambda: (len(result) >= 1)),
    ])
    return result


def prove(facts: Cls, goal: Cl, env: TypeEnv, limits: Limits) -> Proof:
    """факты влекут цель — для списков длины до limits.k_lists"""
    result = _flows.prove(facts=facts, goal=goal, env=env, limits=limits)
    _c.check('rptg.lang.cl:prove', 'ensures', [
        ('result.verdict == "refuted" => result.counterexample != null', lambda: ((not (result.verdict == "refuted")) or (result.counterexample is not None))),
        ('result.bound == limits.k_lists', lambda: (result.bound == limits.k_lists)),
    ])
    return result


def sat(conds: Cls, env: TypeEnv, limits: Limits) -> Sat:
    """выполнимость набора условий и противоречивый поднабор"""
    result = _flows.sat(conds=conds, env=env, limits=limits)
    _c.check('rptg.lang.cl:sat', 'ensures', [
        ('result.verdict == "unsat" => len(result.core) >= 1', lambda: ((not (result.verdict == "unsat")) or (len(result.core) >= 1))),
        ('forall i in result.core: i >= 0 and i < len(conds)', lambda: all(((i >= 0) and (i < len(conds))) for i in result.core)),
    ])
    return result


def strategy(requires: Cls, params: Params, env: TypeEnv) -> StrMap:
    """стратегии Hypothesis по требованиям"""
    result = _flows.strategy(requires=requires, params=params, env=env)
    _c.check('rptg.lang.cl:strategy', 'ensures', [
        ('len(result) == len(params)', lambda: (len(result) == len(params))),
    ])
    return result
