"""Схемы потоков узла rptg.lang.cl.logic.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.logic.yaml — не править руками.
"""
from __future__ import annotations

from ._leaves import decode as c_decode
from ._leaves import schema as c_schema
from ._leaves import script as c_script
from ._leaves import smt as c_smt
from ._leaves import solve as c_solve



def prove(facts, goal, env, limits):
    n1 = [c_smt.term(typed=_x, limits=limits) for _x in facts]
    n2 = [c_schema.facts(term=_x, env=env, limits=limits) for _x in n1]
    n3 = c_smt.term(typed=goal, limits=limits)
    n4 = c_schema.facts(term=n3, env=env, limits=limits)
    n5 = c_script.prove(facts=n2, goal=n4, limits=limits)
    n6 = c_solve.run(smt=n5, limits=limits)
    n7 = c_decode.proof(answer=n6, smt=n5, limits=limits)
    return n7


def sat(conds, env, limits):
    n1 = [c_smt.term(typed=_x, limits=limits) for _x in conds]
    n2 = [c_schema.facts(term=_x, env=env, limits=limits) for _x in n1]
    n3 = c_script.sat(conds=n2, limits=limits)
    n4 = c_solve.run(smt=n3, limits=limits)
    n5 = c_decode.sat(answer=n4, smt=n3)
    return n5
