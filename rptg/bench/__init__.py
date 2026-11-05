"""калибровка операторов: раздел набора на подбор и проверку, задачи калибровки, клетки таблицы, гейт G0

Сгенерировано tools/codegen0.py по design/rptg.bench.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import CalibrationPlan, CalibrationResults, Competence, Config, ReferenceSet, Strings



def plan(reference: ReferenceSet, operators: Strings, cfg: Config) -> CalibrationPlan:
    """раздел набора: задачи по роду, внутри рода — по возрастанию хэша имени; чётные места общего списка — подбор, нечётные — проверка, так каждый род делится поровну; задачи — для каждой задачи набора каждый оператор"""
    _c.check('rptg.bench:plan', 'requires', [
        ('len(reference.items) >= 2', lambda: (len(reference.items) >= 2)),
        ('len(operators) >= 1', lambda: (len(operators) >= 1)),
    ])
    result = _flows.plan(reference=reference, operators=operators, cfg=cfg)
    _c.check('rptg.bench:plan', 'ensures', [
        ('len(result.tasks) == len(reference.items) * len(operators)', lambda: (len(result.tasks) == (len(reference.items) * len(operators)))),
        ('len(result.fit) + len(result.check) == len(reference.items)', lambda: ((len(result.fit) + len(result.check)) == len(reference.items))),
        ('forall i in result.fit: not (i in result.check)', lambda: all((not (i in result.check)) for i in result.fit)),
    ])
    return result


def table(results: CalibrationResults, plan: CalibrationPlan, cfg: Config) -> Competence:
    """итоги → клетки по (оператор, класс) в порядке класса и оператора; победитель рода — лучшая доля успеха, при равенстве дешевле; G0 — победителей больше одного"""
    result = _flows.table(results=results, plan=plan, cfg=cfg)
    _c.check('rptg.bench:table', 'ensures', [
        ('forall c in result.cells: c.ok_fit <= c.n_fit and c.ok_check <= c.n_check', lambda: all(((c.ok_fit <= c.n_fit) and (c.ok_check <= c.n_check)) for c in result.cells)),
        ('forall c in result.cells: c.low_data == (c.n_fit + c.n_check < cfg.routing.n_min)', lambda: all((c.low_data == ((c.n_fit + c.n_check) < cfg.routing.n_min)) for c in result.cells)),
    ])
    return result
