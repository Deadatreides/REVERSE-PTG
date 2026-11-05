"""Схемы потоков узла rptg.plan.choose.

Сгенерировано tools/codegen0.py по design/rptg.plan.choose.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg import lang as u_lang
from rptg.plan import machine as u_machine
from ._leaves import pending as c_pending



def action(state, candidates, assignments, cfg):
    n1 = u_machine.policies(cfg=cfg)
    n2 = c_pending.choose(state=_v.dump(state), candidates=candidates, assignments=assignments, policies=n1, cfg=cfg)
    n3 = u_machine.dispatch(state=state, subject=n2.subject, assignments=n2.assignments, cfg=cfg)
    n4 = u_lang.digest(value=_v.dump(n2.design))
    n5 = c_pending.action(state=_v.dump(state), choice=n2, step=n3, hash=n4)
    return n5
