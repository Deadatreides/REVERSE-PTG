"""Схемы потоков узла rptg.check.code.

Сгенерировано tools/codegen0.py по design/rptg.check.code.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import outcome as c_outcome
from ._leaves import rules as c_rules
from ._leaves import runs as c_runs
from ._leaves import size as c_size



def static(state, answer, cfg):
    n1 = c_rules.check(state=_v.dump(state), answer=answer)
    n2 = c_size.check(state=_v.dump(state), answer=answer, cfg=cfg)
    n3 = c_outcome.static(answer=answer, rules=n1, size=n2)
    return n3


def runs(state, event, cfg):
    n1 = c_runs.read(state=_v.dump(state), event=_v.dump(event), cfg=cfg)
    return n1
