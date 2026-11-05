"""Схемы потоков узла rptg.bench.

Сгенерировано tools/codegen0.py по design/rptg.bench.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg._types import CalibrationPlan, Competence
from ._leaves import gate as c_gate
from rptg import lang as u_lang
from ._leaves import price as c_price
from ._leaves import split as c_split
from ._leaves import tally as c_tally
from ._leaves import tasks as c_tasks



def plan(reference, operators, cfg):
    n1 = [u_lang.digest(value=_v.dump(_x.id)) for _x in reference.items]
    n2 = c_split.halves(reference=reference, digests=n1)
    n3 = c_tasks.make(reference=reference, operators=operators)
    n4 = CalibrationPlan(fit=n2.fit, check=n2.check, tasks=n3)
    return n4


def table(results, plan, cfg):
    n1 = c_tally.count(results=results, plan=plan, cfg=cfg)
    n2 = [c_price.cell(tally=_x) for _x in n1]
    n3 = c_gate.g0(cells=n2)
    n4 = Competence(cells=n2, g0=n3)
    return n4
