"""Лист rptg.talk.context.merge — склейка фактов (С-8: вычислить всё, выбрать в листе).

Функции приняты по карточке design/rptg.talk.context.yaml; обвязку пишет скрипт. Из фактов карты,
разложения и функции на деле непуст один набор: каждый лист на чужом виде задачи отвечает пустым
списком разделов. Отчёт идёт первым: полнота нахождения у малых моделей падает с позицией записи
монотонно (K1: 0,609 на позиции 0 против 0,214 на позиции 17), а отчёт — главное в починке.
"""
from __future__ import annotations

from rptg.talk._types import Facts


def facts(idea: Facts, branch: Facts, leaf: Facts, repair: Facts) -> Facts:
    """Разделы отчёта, затем карты, разложения и функции — подряд."""
    return Facts(sections=repair.sections + idea.sections + branch.sections + leaf.sections)
