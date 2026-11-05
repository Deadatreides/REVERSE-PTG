"""Лист rptg.bench.tally — итоги калибровки → клетки по оператору и классу до цены (LOGIC §6.4).

Функция принята по карточке design/rptg.bench.yaml; обвязку пишет скрипт. Итог вне плана не считается;
повтор пары (задача, оператор) — последний: перезапуск заменяет прежний итог, иначе выборка перестала бы
быть равной. Цену на успех считает лист price — десятичная арифметика своя работа.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.bench._types import Tally

if TYPE_CHECKING:
    from rptg._types import CalibrationPlan, CalibrationResults, Config
    from rptg.bench._types import Tallies


def count(results: CalibrationResults, plan: CalibrationPlan, cfg: Config) -> Tallies:
    """Итоги задач плана: задача в подборе или проверке, иначе итог не считается; повтор пары (задача,
    оператор) — последний. Клетка на (оператор, класс итога) в порядке класса и оператора: n и ok на
    подборе и на проверке, цены итогов клетки по порядку итогов, мало данных — n_fit + n_check < n_min."""
    half = {**{item: "fit" for item in plan.fit}, **{item: "check" for item in plan.check}}
    last = {(r.item, r.operator): r for r in results if r.item in half}
    groups: dict = {}
    for r in last.values():
        g = groups.setdefault((r.class_, r.operator), {"fit": [0, 0], "check": [0, 0], "costs": []})
        g[half[r.item]][0] += 1
        g[half[r.item]][1] += int(r.passed)
        g["costs"].append(r.cost)

    def tally(work, operator, g):
        (n_fit, ok_fit), (n_check, ok_check) = g["fit"], g["check"]
        return Tally(operator=operator, class_=work, n_fit=n_fit, ok_fit=ok_fit, n_check=n_check, ok_check=ok_check, costs=g["costs"],
                     low_data=n_fit + n_check < cfg.routing.n_min)

    return [tally(work, operator, groups[(work, operator)]) for work, operator in sorted(groups)]
