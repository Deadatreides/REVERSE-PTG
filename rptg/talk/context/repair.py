"""Лист rptg.talk.context.repair — контекст починки (CONTEXT_MODEL §4, LOGIC §8.4).

Функции приняты по карточке design/rptg.talk.context.yaml; обвязку пишет скрипт. Отчёт шаблона
самодостаточен: место, фрагмент, ожидание, контрпример. Прежнего ответа модель не получает (F1) —
ключа для него среди разделов нет.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.talk._types import Fact, Facts

if TYPE_CHECKING:
    from rptg._types import Json


def facts(task: Json) -> Facts:
    """Есть отчёт — раздел report с ним как есть; нет — пусто."""
    if task.get("report") is None:
        return Facts(sections=[])
    return Facts(sections=[Fact(key="report", value=task["report"])])
