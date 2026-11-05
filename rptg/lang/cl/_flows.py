"""Схемы потоков узла rptg.lang.cl.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg._types import ClInfo
from ._leaves import evaluate as c_evaluate
from . import logic as c_logic
from ._leaves import measure as c_measure
from ._leaves import parse as c_parse
from ._leaves import python as c_python
from . import strategy as c_strategy
from ._leaves import typecheck as c_typecheck



def info(text, env):
    n1 = c_parse.parse(text=text)
    n2 = c_typecheck.typecheck(parsed=n1, env=env)
    n3 = c_measure.measure(parsed=n1)
    n4 = ClInfo(ok=n2.ok, errors=n2.errors, type=n2.type, nodes=n3.nodes, quant=n3.quant, nonlin=n3.nonlin, arith=n3.arith, strings=n3.strings, names=n3.names)
    return n4


def eval(text, env, values):
    n1 = c_parse.parse(text=text)
    n2 = c_typecheck.typecheck(parsed=n1, env=env)
    n3 = c_evaluate.evaluate(typed=n2, values=_v.dump(values))
    return n3


def python(text, env):
    n1 = c_parse.parse(text=text)
    n2 = c_typecheck.typecheck(parsed=n1, env=env)
    n3 = c_python.python(typed=n2)
    return n3


def prove(facts, goal, env, limits):
    n1 = [c_parse.parse(text=_x) for _x in facts]
    n2 = [c_typecheck.typecheck(parsed=_x, env=env) for _x in n1]
    n3 = c_parse.parse(text=goal)
    n4 = c_typecheck.typecheck(parsed=n3, env=env)
    n5 = c_logic.prove(facts=n2, goal=n4, env=env, limits=limits)
    return n5


def sat(conds, env, limits):
    n1 = [c_parse.parse(text=_x) for _x in conds]
    n2 = [c_typecheck.typecheck(parsed=_x, env=env) for _x in n1]
    n3 = c_logic.sat(conds=n2, env=env, limits=limits)
    return n3


def strategy(requires, params, env):
    n1 = [c_parse.parse(text=_x) for _x in requires]
    n2 = [c_typecheck.typecheck(parsed=_x, env=env) for _x in n1]
    n3 = c_strategy.strategy(requires=n2, params=params, env=env)
    return n3
