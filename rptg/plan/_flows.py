"""Схемы потоков узла rptg.plan.

Сгенерировано tools/codegen0.py по design/rptg.plan.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg import check as u_check
from . import choose as c_choose
from . import machine as c_machine
from ._leaves import queue as c_queue
from . import route as c_route



def candidates(state, cfg):
    n1 = c_queue.ready(state=_v.dump(state), cfg=cfg)
    n2 = c_route.score(state=_v.dump(state), ready=n1, cfg=cfg)
    return n2


def assign(candidate, table, cfg):
    n1 = c_route.assign(candidate=candidate, table=table, cfg=cfg)
    return n1


def pick(state, candidates, assignments, cfg):
    n1 = c_choose.action(state=state, candidates=candidates, assignments=assignments, cfg=cfg)
    return n1


def transition(state, event, evidence, cfg):
    n1 = u_check.answer(event=event)
    n2 = c_machine.absorb(state=state, event=event, evidence=evidence, answer=n1, cfg=cfg)
    n3 = c_route.kinds(state=_v.dump(n2.state), node=n2.route, cfg=cfg)
    n4 = c_machine.settle(before=state, absorbed=n2, kinds=n3, cfg=cfg)
    n5 = c_machine.recheck(settled=n4, cfg=cfg)
    n6 = c_machine.close(before=state, absorbed=n2, settled=n5, evidence=evidence, cfg=cfg)
    return n6
