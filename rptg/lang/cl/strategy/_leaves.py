"""Финальные дети узла rptg.lang.cl.strategy в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.strategy.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import bounds as _m_bounds
from . import gen as _m_gen

if TYPE_CHECKING:
    from rptg._types import Params, StrMap, TypeEnv
    from rptg.lang.cl._types import Typeds
    from rptg.lang.cl.strategy._types import Bounds



class bounds:
    """Лист rptg.lang.cl.strategy.bounds: операции в обёртках условий."""

    @staticmethod
    def bounds(requires: Typeds) -> Bounds:
        """сравнения в конъюнкции требований и в теле forall над путём → самые тесные границы по порядку: путь, что, сначала min; строгое сравнение у нецелого пути — без шага; путь с индексом, exists и прочее остаются фильтру"""
        result = _m_bounds.bounds(requires=requires)
        _c.check('rptg.lang.cl.strategy.bounds:bounds', 'ensures', [
            ('forall b in result: len(b.name) >= 1', lambda: all((len(b.name) >= 1) for b in result)),
        ])
        return result


class gen:
    """Лист rptg.lang.cl.strategy.gen: операции в обёртках условий."""

    @staticmethod
    def gen(params: Params, bounds: Bounds, env: TypeEnv) -> StrMap:
        """по стратегии на параметр; граница ищется по пути места (поле — через точку, элемент списка — []); границы схемы тоже учитываются, из двух берётся более тесная"""
        result = _m_gen.gen(params=params, bounds=bounds, env=env)
        _c.check('rptg.lang.cl.strategy.gen:gen', 'ensures', [
            ('len(result) == len(params)', lambda: (len(result) == len(params))),
        ])
        return result
