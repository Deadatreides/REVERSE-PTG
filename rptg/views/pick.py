"""Лист rptg.views.pick — представление по виду запроса.

Функция принята по карточке design/rptg.views.yaml; обвязку пишет скрипт. Схема ветвлений не знает (С-8):
все четыре представления посчитаны, здесь выбирается одно.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import View

if TYPE_CHECKING:
    from rptg._types import Json, ViewQuery


def view(query: ViewQuery, status: Json, node: Json, graph: Json, competence: Json) -> View:
    """Вид запроса и данные его представления."""
    return View(kind=query.kind, data={"status": status, "node": node, "graph": graph, "competence": competence}[query.kind])
