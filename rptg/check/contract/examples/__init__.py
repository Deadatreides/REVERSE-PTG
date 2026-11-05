"""П7: примеры операций детей (для карты — корня), включая примеры пользователя

Сгенерировано tools/codegen0.py по design/rptg.check.contract.examples.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json



def check(state: Json, answer: Answer, form: Evidences) -> Evidences:
    """П7: примеры проходят типы, требования и гарантии своих операций (I16); примеров не меньше I15"""
    result = _flows.check(state=state, answer=answer, form=form)
    _c.check('rptg.check.contract.examples:check', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "P7"', lambda: all((e.check == "P7") for e in result)),
    ])
    return result
