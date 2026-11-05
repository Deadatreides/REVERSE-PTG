"""Лист rptg.bench.tasks — задачи калибровки (LOGIC §6.4).

Функция принята по карточке design/rptg.bench.yaml; обвязку пишет скрипт. Сравнение операторов — только
при равной выборке: каждый оператор решает каждую задачу набора.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Task

if TYPE_CHECKING:
    from rptg._types import ReferenceSet, Strings
    from rptg.bench._types import CalTasks


def make(reference: ReferenceSet, operators: Strings) -> CalTasks:
    """Для каждой задачи набора по порядку — каждый оператор по порядку: функция единственной операции
    карточки задачи, исполнитель, попытка 1, основная формулировка."""
    return [Task(subject=f"function:{item.card.id}:{item.card.ops[0].name}", kind="function", role="implementer", operator=operator,
                 attempt=1, wording="primary") for item in reference.items for operator in operators]
