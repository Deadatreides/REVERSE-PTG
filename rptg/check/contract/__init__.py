"""договоры на рёбрах и операциях: совместимость данных (П3), условий (П4, П5 без блокировки) и примеры (П7) — через язык условий и типов

Сгенерировано tools/codegen0.py по design/rptg.check.contract.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json



def data(state: Json, answer: Answer, form: Evidences, cfg: Config, edges: Json) -> Evidences:
    """П3: тип источника ⊑ типу места назначения на каждом ребре схем разложения и на каждом ребре из edges; если нечего проверять или П1 провалена — пусто"""
    result = _flows.data(state=state, answer=answer, form=form, cfg=cfg, edges=edges)
    _c.check('rptg.check.contract:data', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "P3"', lambda: all((e.check == "P3") for e in result)),
    ])
    return result


def logic(state: Json, answer: Answer, form: Evidences, cfg: Config) -> Evidences:
    """П4: на каждом узле схемы факты выше по потоку влекут требования вызываемого (I13), условия каждой операции детей выполнимы (I14); П5: факты схемы влекут гарантии узла — считается, не блокирует. Для карты — только выполнимость операций корня"""
    result = _flows.logic(state=state, answer=answer, form=form, cfg=cfg)
    _c.check('rptg.check.contract:logic', 'ensures', [
        ('len(result) <= 2', lambda: (len(result) <= 2)),
        ('forall e in result: e.check == "P4" or e.check == "P5"', lambda: all(((e.check == "P4") or (e.check == "P5")) for e in result)),
    ])
    return result


def examples(state: Json, answer: Answer, form: Evidences, cfg: Config) -> Evidences:
    """П7: примеры операций детей (для карты — корня), включая примеры пользователя, проходят типы, требования и гарантии (I16); примеров не меньше I15"""
    result = _flows.examples(state=state, answer=answer, form=form, cfg=cfg)
    _c.check('rptg.check.contract:examples', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "P7"', lambda: all((e.check == "P7") for e in result)),
    ])
    return result
