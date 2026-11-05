"""Лист rptg.bench.price — цена на успех клетки таблицы компетенций (LOGIC §6.4).

Функция принята по карточке design/rptg.bench.yaml; обвязку пишет скрипт. Цена на успех — все расходы
клетки на число успехов, как c = total_cost / solved у arch2 (fitness.py); успехов нет — у arch2
бесконечность, запись Decimal её не выражает: расходы всех попыток. Десятичные — с масштабом, как у
модуля decimal (пример пользователя: «0.0020»); модуль decimal узлу не разрешён — арифметика в целых.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Cell

if TYPE_CHECKING:
    from rptg.bench._types import Tally


def cell(tally: Tally) -> Cell:
    """Клетка таблицы: всё, кроме цен, — как у счёта; цена на успех — сумма цен на число успехов (подбор
    и проверка), успехов нет — сумма цен. Запись: сумма — в масштабе самой длинной цены; частное — в нём,
    если точно, иначе в стольких знаках, сколько нужно для точного, но не больше max(масштаб, 18); не
    уложилось — округление половины к чётному на последнем знаке."""
    def parse(text):
        whole, _, frac = text.partition(".")
        return int(whole + frac), len(frac)

    parsed = [parse(cost) for cost in tally.costs]
    scale = max((s for _, s in parsed), default=0)
    total = sum(n * 10 ** (scale - s) for n, s in parsed)
    wins, top = tally.ok_fit + tally.ok_check, max(scale, 18)
    d = wins or 1
    places = next((p for p in range(scale, top + 1) if total * 10 ** (p - scale) % d == 0), top)
    q, r = divmod(total * 10 ** (places - scale), d)
    value = q + int(2 * r > d or 2 * r == d and q % 2 == 1)
    digits = str(value).rjust(places + 1, "0")
    text = digits[:-places] + "." + digits[-places:] if places else digits
    return Cell(operator=tally.operator, class_=tally.class_, n_fit=tally.n_fit, ok_fit=tally.ok_fit, n_check=tally.n_check,
                ok_check=tally.ok_check, cost_per_success=text, low_data=tally.low_data)
