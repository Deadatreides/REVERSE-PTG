"""Схемы потоков узла rptg.check.contract.logic.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.logic.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import equal as c_equal
from ._leaves import facts as c_facts
from ._leaves import feasible as c_feasible
from rptg import lang as u_lang
from ._leaves import outcome as c_outcome
from ._leaves import render as c_render



def check(state, answer, form, cfg):
    n1 = c_facts.plan(state=_v.dump(state), answer=answer, form=form, cfg=cfg)
    n2 = c_equal.expand(plan=n1, cfg=cfg)
    n3 = c_render.obligations(plan=n2)
    n4 = c_feasible.jobs(state=_v.dump(state), answer=answer, form=form)
    n5 = [u_lang.cl_prove(facts=_x.facts, goal=_x.goal, env=_x.env, limits=cfg.limits) for _x in n3.proofs]
    n6 = [u_lang.cl_sat(conds=_x.conds, env=_x.env, limits=cfg.limits) for _x in n4]
    n7 = [u_lang.cl_prove(facts=_x.facts, goal=_x.goal, env=_x.env, limits=cfg.limits) for _x in n3.refines]
    n8 = c_outcome.verdict(obligations=n3, proofs=n5, empties=n4, sats=n6, refines=n7)
    return n8
