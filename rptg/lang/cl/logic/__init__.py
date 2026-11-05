"""доказательство и выполнимость через текст SMT-LIB и решатель Z3

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.logic.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Limits, Proof, Sat, TypeEnv
    from rptg.lang.cl._types import Typed, Typeds



def prove(facts: Typeds, goal: Typed, env: TypeEnv, limits: Limits) -> Proof:
    """факты влекут цель — для списков длины до limits.k_lists"""
    result = _flows.prove(facts=facts, goal=goal, env=env, limits=limits)
    _c.check('rptg.lang.cl.logic:prove', 'ensures', [
        ('result.verdict == "refuted" => result.counterexample != null', lambda: ((not (result.verdict == "refuted")) or (result.counterexample is not None))),
        ('result.bound == limits.k_lists', lambda: (result.bound == limits.k_lists)),
    ])
    return result


def sat(conds: Typeds, env: TypeEnv, limits: Limits) -> Sat:
    """выполнимость; при невыполнимости — номера строк противоречивого поднабора"""
    result = _flows.sat(conds=conds, env=env, limits=limits)
    _c.check('rptg.lang.cl.logic:sat', 'ensures', [
        ('result.verdict == "unsat" => len(result.core) >= 1', lambda: ((not (result.verdict == "unsat")) or (len(result.core) >= 1))),
        ('forall i in result.core: i >= 0 and i < len(conds)', lambda: all(((i >= 0) and (i < len(conds))) for i in result.core)),
    ])
    return result
