"""Лист rptg.views.status — сводка проекта для командной строки (ARCHITECTURE §8, `rptg status`).

Функция принята по карточке design/rptg.views.yaml; обвязку пишет скрипт. Поля — ровно поля примера
пользователя у операции view корня.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json


def count(state: Json) -> Json:
    """Фаза, узлов (карточек), элементов принято и запланировано (состояние planned), расход и лимит
    бюджета — ровно эти поля."""
    states = [e["state"] for e in state["elements"].values()]
    return {"phase": state["phase"], "nodes": len(state["cards"]), "accepted": states.count("accepted"),
            "planned": states.count("planned"), "spent": state["budget"]["spent"], "limit": state["budget"]["limit"]}
