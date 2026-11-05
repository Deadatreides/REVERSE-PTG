"""Финальные дети узла rptg.bench в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.bench.yaml — не править руками.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import split as _m_split
from . import tasks as _m_tasks
from . import tally as _m_tally
from . import price as _m_price
from . import gate as _m_gate

if TYPE_CHECKING:
    from rptg._types import CalibrationPlan, CalibrationResults, Cell, Config, ReferenceSet, Strings
    from rptg.bench._types import CalTasks, Cells, Digests, Halves, Tallies, Tally



class split:
    """Лист rptg.bench.split: операции в обёртках условий."""

    @staticmethod
    def halves(reference: ReferenceSet, digests: Digests) -> Halves:
        """задачи набора по роду, внутри рода — по возрастанию хэша имени (digests — хэши имён по порядку набора), равные хэши — по имени; чётные места общего списка — подбор, нечётные — проверка: каждый род делится поровну, ±1 (К-8, утверждено 02.10.2026)"""
        _c.check('rptg.bench.split:halves', 'requires', [
            ('len(digests) == len(reference.items)', lambda: (len(digests) == len(reference.items))),
        ])
        result = _m_split.halves(reference=reference, digests=digests)
        _c.check('rptg.bench.split:halves', 'ensures', [
            ('len(result.fit) + len(result.check) == len(reference.items)', lambda: ((len(result.fit) + len(result.check)) == len(reference.items))),
            ('len(result.fit) >= len(result.check)', lambda: (len(result.fit) >= len(result.check))),
            ('forall i in result.fit: not (i in result.check)', lambda: all((not (i in result.check)) for i in result.fit)),
        ])
        return result


class tasks:
    """Лист rptg.bench.tasks: операции в обёртках условий."""

    @staticmethod
    def make(reference: ReferenceSet, operators: Strings) -> CalTasks:
        """для каждой задачи набора по порядку — каждый оператор по порядку: функция единственной операции карточки задачи, исполнитель, попытка 1, основная формулировка"""
        _c.check('rptg.bench.tasks:make', 'requires', [
            ('forall i in reference.items: len(i.card.ops) == 1', lambda: all((len(i.card.ops) == 1) for i in reference.items)),
        ])
        result = _m_tasks.make(reference=reference, operators=operators)
        _c.check('rptg.bench.tasks:make', 'ensures', [
            ('len(result) == len(reference.items) * len(operators)', lambda: (len(result) == (len(reference.items) * len(operators)))),
        ])
        return result


class tally:
    """Лист rptg.bench.tally: операции в обёртках условий."""

    @staticmethod
    def count(results: CalibrationResults, plan: CalibrationPlan, cfg: Config) -> Tallies:
        """итоги задач плана: задача в подборе или проверке, иначе итог не считается; повтор пары (задача, оператор) — последний (перезапуск заменяет). Клетка на (оператор, класс итога) в порядке класса и оператора: n и ok на подборе и на проверке, цены итогов клетки по порядку итогов, мало данных — n_fit + n_check < n_min"""
        result = _m_tally.count(results=results, plan=plan, cfg=cfg)
        _c.check('rptg.bench.tally:count', 'ensures', [
            ('forall t in result: t.ok_fit <= t.n_fit and t.ok_check <= t.n_check', lambda: all(((t.ok_fit <= t.n_fit) and (t.ok_check <= t.n_check)) for t in result)),
            ('forall t in result: len(t.costs) == t.n_fit + t.n_check', lambda: all((len(t.costs) == (t.n_fit + t.n_check)) for t in result)),
            ('forall t in result: t.low_data == (t.n_fit + t.n_check < cfg.routing.n_min)', lambda: all((t.low_data == ((t.n_fit + t.n_check) < cfg.routing.n_min)) for t in result)),
        ])
        return result


class price:
    """Лист rptg.bench.price: операции в обёртках условий."""

    @staticmethod
    def cell(tally: Tally) -> Cell:
        """клетка таблицы: всё, кроме цен, — как у счёта; цена на успех — сумма цен на число успехов (подбор и проверка), успехов нет — сумма цен. Запись: сумма — в масштабе самой длинной цены; частное — в нём, если точно, иначе в стольких знаках, сколько нужно для точного, но не больше max(масштаб, 18); не уложилось — округление половины к чётному на последнем знаке"""
        _c.check('rptg.bench.price:cell', 'requires', [
            ('tally.ok_fit <= tally.n_fit and tally.ok_check <= tally.n_check', lambda: ((tally.ok_fit <= tally.n_fit) and (tally.ok_check <= tally.n_check))),
            ('len(tally.costs) == tally.n_fit + tally.n_check', lambda: (len(tally.costs) == (tally.n_fit + tally.n_check))),
            ('forall c in tally.costs: c >= 0', lambda: all((Decimal(c) >= 0) for c in tally.costs)),
        ])
        result = _m_price.cell(tally=tally)
        _c.check('rptg.bench.price:cell', 'ensures', [
            ('result.operator == tally.operator and result.class == tally.class', lambda: ((result.operator == tally.operator) and (result.class_ == tally.class_))),
            ('result.n_fit == tally.n_fit and result.ok_fit == tally.ok_fit and result.n_check == tally.n_check and result.ok_check == tally.ok_check', lambda: ((((result.n_fit == tally.n_fit) and (result.ok_fit == tally.ok_fit)) and (result.n_check == tally.n_check)) and (result.ok_check == tally.ok_check))),
            ('result.low_data == tally.low_data', lambda: (result.low_data == tally.low_data)),
            ('result.cost_per_success >= 0', lambda: (Decimal(result.cost_per_success) >= 0)),
        ])
        return result


class gate:
    """Лист rptg.bench.gate: операции в обёртках условий."""

    @staticmethod
    def g0(cells: Cells) -> bool:
        """победитель класса — наибольшая доля успеха на подборе (n_fit = 0 — доля 0), при равенстве — дешевле на успех (сравнение записей точное), затем по имени оператора; G0 — разных победителей у классов больше одного"""
        result = _m_gate.g0(cells=cells)
        _c.check('rptg.bench.gate:g0', 'ensures', [
            ('len(cells) == 0 => not result', lambda: ((not (len(cells) == 0)) or (not result))),
        ])
        return result
