"""проверки кода: статика функции (Э1) и толкование прогонов в песочнице — mypy (Э1), примеры (Э2), свойства (Э3), сборка (Э6) с распределением вины

Сгенерировано tools/codegen0.py по design/rptg.check.code.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json



def static(state: Json, answer: Answer, cfg: Config) -> Evidences:
    """Э1 по коду функции из ответа: одно определение по сигнатуре карточки, импорты по белому списку, запреты, строки кода — функция договора, сложность блока; ответ без блока python — провал; для других ответов — пусто"""
    result = _flows.static(state=state, answer=answer, cfg=cfg)
    _c.check('rptg.check.code:static', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "E1"', lambda: all((e.check == "E1") for e in result)),
    ])
    return result


def runs(state: Json, event: Json, cfg: Config) -> Evidences:
    """доказательства из отчёта прогона в песочнице: Э1 mypy, Э2 примеры, Э3 свойства, Э6 сборка с виновным по первому нарушению трассы; нет отчёта — unknown; для другого события — пусто"""
    result = _flows.runs(state=state, event=event, cfg=cfg)
    _c.check('rptg.check.code:runs', 'ensures', [
        ('forall e in result: e.check == "E1" or e.check == "E2" or e.check == "E3" or e.check == "E6"', lambda: all(((((e.check == "E1") or (e.check == "E2")) or (e.check == "E3")) or (e.check == "E6")) for e in result)),
    ])
    return result
