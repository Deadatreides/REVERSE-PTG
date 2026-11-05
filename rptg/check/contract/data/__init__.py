"""П3: совместимость данных на каждом ребре схем разложения и на отдельных рёбрах контрольных случаев

Сгенерировано tools/codegen0.py по design/rptg.check.contract.data.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json



def check(state: Json, answer: Answer, form: Evidences, edges: Json) -> Evidences:
    """П3: тип источника ⊑ типу места назначения на каждом ребре схем разложения и на каждом ребре из edges; если нечего проверять или П1 провалена — пусто"""
    result = _flows.check(state=state, answer=answer, form=form, edges=edges)
    _c.check('rptg.check.contract.data:check', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "P3"', lambda: all((e.check == "P3") for e in result)),
    ])
    return result
