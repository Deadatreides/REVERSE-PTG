"""П1: извлечение ответа модели из сырого текста и его форма — схема вида задачи, разбор и типы условий, видимость типов, однозначность коротких имён

Сгенерировано tools/codegen0.py по design/rptg.check.answer.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json



def extract(event: Json) -> Answer:
    """извлечь ответ из события: единственный блок JSON (карта, разложение) или python (функция); узел и операция — из предмета задачи; обрыв по пределу длины — пометка, не ошибка; событие без ответа модели — вид none"""
    result = _flows.extract(event=event)
    _c.check('rptg.check.answer:extract', 'ensures', [
        ('result.ok => result.error == null', lambda: ((not result.ok) or (result.error is None))),
        ('not result.ok => result.error != null', lambda: ((not (not result.ok)) or (result.error is not None))),
        ('result.ok and result.kind == "function" => result.code != null', lambda: ((not (result.ok and (result.kind == "function"))) or (result.code is not None))),
        ('result.ok and (result.kind == "map" or result.kind == "design") => result.value != null', lambda: ((not (result.ok and ((result.kind == "map") or (result.kind == "design")))) or (result.value is not None))),
    ])
    return result


def form(state: Json, answer: Answer, cfg: Config) -> Evidences:
    """П1 по извлечённому ответу карты или разложения: схема вида задачи с закрытыми записями, разбор и типы всех условий, переменная квантора не совпадает с параметром, видимость типов, однозначность коротких имён; для остальных видов — пусто"""
    result = _flows.form(state=state, answer=answer, cfg=cfg)
    _c.check('rptg.check.answer:form', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "P1"', lambda: all((e.check == "P1") for e in result)),
    ])
    return result
