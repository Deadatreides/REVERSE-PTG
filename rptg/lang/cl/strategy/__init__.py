"""стратегии Hypothesis: сравнения с константами становятся границами

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.strategy.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Params, StrMap, TypeEnv
    from rptg.lang.cl._types import Typeds



def strategy(requires: Typeds, params: Params, env: TypeEnv) -> StrMap:
    """по стратегии на параметр; сложные условия остаются фильтру теста"""
    result = _flows.strategy(requires=requires, params=params, env=env)
    _c.check('rptg.lang.cl.strategy:strategy', 'ensures', [
        ('len(result) == len(params)', lambda: (len(result) == len(params))),
    ])
    return result
