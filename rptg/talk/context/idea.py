"""Лист rptg.talk.context.idea — факты задачи карты (LOGIC §8.1, задача «К карта»).

Функции приняты по карточке design/rptg.talk.context.yaml; обвязку пишет скрипт. Архитектор карты
получает замысел и приёмочные примеры; правила метода и схема ответа — в префиксе подсказки.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.talk._types import Fact, Facts

if TYPE_CHECKING:
    from rptg._types import Json, Task


def facts(task: Task, state: Json) -> Facts:
    """Карта — разделы idea и examples (примеры пользователя по операциям); другой вид — пусто."""
    if task.kind != "map":
        return Facts(sections=[])
    return Facts(sections=[Fact(key="idea", value=state["idea"]), Fact(key="examples", value=state["user_examples"])])
