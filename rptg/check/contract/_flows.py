"""Схемы потоков узла rptg.check.contract.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from . import data as c_data
from . import examples as c_examples
from . import logic as c_logic



def data(state, answer, form, cfg, edges):
    n1 = c_data.check(state=_v.dump(state), answer=answer, form=form, edges=_v.dump(edges))
    return n1


def logic(state, answer, form, cfg):
    n1 = c_logic.check(state=_v.dump(state), answer=answer, form=form, cfg=cfg)
    return n1


def examples(state, answer, form, cfg):
    n1 = c_examples.check(state=_v.dump(state), answer=answer, form=form)
    return n1
