"""представления для окна и командной строки: сводка, узел, граф сети с назначениями и состояниями, таблица компетенций

Сгенерировано tools/codegen0.py по design/rptg.views.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Config, State, View, ViewQuery



def show(state: State, query: ViewQuery, cfg: Config) -> View:
    """представление по запросу"""
    result = _flows.show(state=state, query=query, cfg=cfg)
    _c.check('rptg.views:show', 'ensures', [
        ('result.kind == query.kind', lambda: (result.kind == query.kind)),
    ])
    return result
