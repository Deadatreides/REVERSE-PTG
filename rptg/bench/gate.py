"""Лист rptg.bench.gate — гейт G0: у разных классов разные победители (LOGIC §6.4).

Функция принята по карточке design/rptg.bench.yaml; обвязку пишет скрипт. Победитель — по доле успеха на
подборе: в experiment14 таблица «род → модель» обучается на train и применяется к test, иначе это выбор
задним числом; проверка в выбор не входит. Цены сравниваются по числу и точно — в целых с общим
масштабом («0.0020» и «0.002» равны).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg.bench._types import Cells


def g0(cells: Cells) -> bool:
    """Победитель класса — наибольшая доля успеха на подборе (n_fit = 0 — доля 0), при равенстве —
    дешевле на успех (сравнение записей точное), затем по имени оператора; G0 — разных победителей у
    классов больше одного."""
    scale = max((len(c.cost_per_success.partition(".")[2]) for c in cells), default=0)

    def key(c):
        whole, _, frac = c.cost_per_success.partition(".")
        rate = c.ok_fit / c.n_fit if c.n_fit else 0.0
        return -rate, int(whole + frac) * 10 ** (scale - len(frac)), c.operator

    winners = {min((c for c in cells if c.class_ == work), key=key).operator for work in {c.class_ for c in cells}}
    return len(winners) > 1
