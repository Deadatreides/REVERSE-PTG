"""Схемы потоков узла rptg.lang.cl.strategy.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.strategy.yaml — не править руками.
"""
from __future__ import annotations

from ._leaves import bounds as c_bounds
from ._leaves import gen as c_gen



def strategy(requires, params, env):
    n1 = c_bounds.bounds(requires=requires)
    n2 = c_gen.gen(params=params, bounds=n1, env=env)
    return n2
