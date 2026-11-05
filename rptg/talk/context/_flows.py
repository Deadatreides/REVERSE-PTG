"""Схемы потоков узла rptg.talk.context.

Сгенерировано tools/codegen0.py по design/rptg.talk.context.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import branch as c_branch
from ._leaves import idea as c_idea
from ._leaves import leaf as c_leaf
from ._leaves import merge as c_merge
from ._leaves import repair as c_repair



def facts(task, state, cfg):
    n1 = c_idea.facts(task=task, state=_v.dump(state))
    n2 = c_branch.facts(task=task, state=_v.dump(state), cfg=_v.dump(cfg))
    n3 = c_leaf.facts(task=task, state=_v.dump(state), cfg=_v.dump(cfg))
    n4 = c_repair.facts(task=_v.dump(task))
    n5 = c_merge.facts(idea=n1, branch=n2, leaf=n3, repair=n4)
    return n5
