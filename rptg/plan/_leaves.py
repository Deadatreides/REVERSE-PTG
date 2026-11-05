"""Финальные дети узла rptg.plan в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.plan.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import queue as _m_queue

if TYPE_CHECKING:
    from rptg._types import Config, Json
    from rptg.plan._types import Ready



class queue:
    """Лист rptg.plan.queue: операции в обёртках условий."""

    @staticmethod
    def ready(state: Json, cfg: Config) -> Ready:
        """NEW и MAP — карта корня, после её приёмки разложение корня (архитектор); MAP_REVIEW, PAUSED, DONE — пусто; DESIGN — разложения по уровням сверху вниз, внутри уровня по пути; BUILD и E2E — разложения, затем функции по пути, затем сборки, чьи дети все приняты, снизу вверх; элемент годен, если его состояние planned, writing, form_retry, repairing, escalated, stale или checking и он не ждёт пользователя"""
        result = _m_queue.ready(state=state, cfg=cfg)
        _c.check('rptg.plan.queue:ready', 'ensures', [
            ('forall r in result: r.level >= 1', lambda: all((r.level >= 1) for r in result)),
        ])
        return result
