"""П4 и П5: обязательства на каждом узле схемы (I13), выполнимость условий операций детей (I14), уточнение (П5, не блокирует)

Сгенерировано tools/codegen0.py по design/rptg.check.contract.logic.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json



def check(state: Json, answer: Answer, form: Evidences, cfg: Config) -> Evidences:
    """П4: на каждом узле схемы факты выше по потоку влекут требования вызываемого (I13), условия каждой операции детей выполнимы (I14); П5: факты схемы влекут гарантии узла — считается, не блокирует. Для карты — только выполнимость операций корня"""
    result = _flows.check(state=state, answer=answer, form=form, cfg=cfg)
    _c.check('rptg.check.contract.logic:check', 'ensures', [
        ('len(result) <= 2', lambda: (len(result) <= 2)),
        ('forall e in result: e.check == "P4" or e.check == "P5"', lambda: all(((e.check == "P4") or (e.check == "P5")) for e in result)),
    ])
    return result
