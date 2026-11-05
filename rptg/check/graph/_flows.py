"""Схемы потоков узла rptg.check.graph.

Сгенерировано tools/codegen0.py по design/rptg.check.graph.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import impact as c_impact
from ._leaves import links as c_links
from ._leaves import outcome as c_outcome
from ._leaves import reach as c_reach
from ._leaves import tree as c_tree



def structure(state, answer, form, cfg):
    n1 = c_tree.check(state=_v.dump(state), answer=answer, form=form, cfg=cfg)
    n2 = c_links.check(state=_v.dump(state), answer=answer, form=form)
    n3 = c_outcome.structure(answer=answer, form=form, tree=n1, links=n2)
    return n3


def dead_ops(state):
    n1 = c_reach.dead_ops(state=_v.dump(state))
    return n1


def stale(state, changed):
    n1 = c_impact.stale(state=_v.dump(state), changed=changed)
    return n1
