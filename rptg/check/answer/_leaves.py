"""Финальные дети узла rptg.check.answer в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.answer.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import raw as _m_raw
from . import shape as _m_shape
from . import conds as _m_conds
from . import names as _m_names
from . import judge as _m_judge

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json, Strings
    from rptg.check._types import ValidateJobs, Validations
    from rptg.check.answer._types import ClInfos, CondJobs



class raw:
    """Лист rptg.check.answer.raw: операции в обёртках условий."""

    @staticmethod
    def extract(event: Json) -> Answer:
        """извлечь ответ: мысли модели снимаются до поиска блоков — закрытые <think>…</think> целиком, у незакрытого <think> только тег, если дальше идёт ответ (блок или JSON), иначе всё после него (рассуждение оборвано); карта и разложение — весь текст как JSON или единственный блок json; функция — единственный блок python (метки py, python3); метка — без учёта регистра; блок без метки — только когда помеченных нет и он один; несколько блоков — провал формы, а не выбор; у разложения узел берётся из предмета; обрыв по пределу длины и отказ — пометки с причиной"""
        result = _m_raw.extract(event=event)
        _c.check('rptg.check.answer.raw:extract', 'ensures', [
            ('result.ok => result.error == null', lambda: ((not result.ok) or (result.error is None))),
            ('not result.ok => result.error != null', lambda: ((not (not result.ok)) or (result.error is not None))),
            ('result.ok and result.kind == "function" => result.code != null', lambda: ((not (result.ok and (result.kind == "function"))) or (result.code is not None))),
            ('result.ok and (result.kind == "map" or result.kind == "design") => result.value != null', lambda: ((not (result.ok and ((result.kind == "map") or (result.kind == "design")))) or (result.value is not None))),
        ])
        return result


class shape:
    """Лист rptg.check.answer.shape: операции в обёртках условий."""

    @staticmethod
    def jobs(state: Json, answer: Answer) -> ValidateJobs:
        """ответ разложения — тип Design, карты — MapAnswer; окружение — схемы типов метода, у каждой записи additionalProperties: false; ответ не извлечён или другого вида — заданий нет"""
        result = _m_shape.jobs(state=state, answer=answer)
        _c.check('rptg.check.answer.shape:jobs', 'ensures', [
            ('len(result) <= 1', lambda: (len(result) <= 1)),
        ])
        return result


class conds:
    """Лист rptg.check.answer.conds: операции в обёртках условий."""

    @staticmethod
    def jobs(state: Json, answer: Answer, checked: Validations) -> CondJobs:
        """разложение — условия операций детей, карта — условия операций корня; видимые типы — Decimal, Json, типы строгих предков узла из состояния и новые типы ответа; ответ не прошёл схему — заданий нет"""
        result = _m_conds.jobs(state=state, answer=answer, checked=checked)
        return result


class names:
    """Лист rptg.check.answer.names: операции в обёртках условий."""

    @staticmethod
    def problems(state: Json, answer: Answer, checked: Validations) -> Strings:
        """по годному ответу: тип параметра, результата и ссылки в схеме нового типа видим (§2.5); короткое имя операции в схеме находится ровно одно — среди детей, потом uses узла (§2.3); параметр не result и не слово Python; переменная квантора не совпадает с параметром и result; ответ не прошёл схему — пусто"""
        result = _m_names.problems(state=state, answer=answer, checked=checked)
        return result


class judge:
    """Лист rptg.check.answer.judge: операции в обёртках условий."""

    @staticmethod
    def form(answer: Answer, shape: ValidateJobs, checked: Validations, problems: Strings, conds: CondJobs, infos: ClInfos) -> Evidences:
        """не карта и не разложение — пусто; шаг split — unknown; не извлечено — fail с причиной (и пометкой обрыва); не по схеме, нарушения имён, неразобранные условия — fail со списком; иначе pass. Хэш — заглушка, его ставит verdict"""
        _c.check('rptg.check.answer.judge:form', 'requires', [
            ('len(checked) == len(shape)', lambda: (len(checked) == len(shape))),
            ('len(infos) == len(conds)', lambda: (len(infos) == len(conds))),
        ])
        result = _m_judge.form(answer=answer, shape=shape, checked=checked, problems=problems, conds=conds, infos=infos)
        _c.check('rptg.check.answer.judge:form', 'ensures', [
            ('len(result) <= 1', lambda: (len(result) <= 1)),
            ('forall e in result: e.check == "P1"', lambda: all((e.check == "P1") for e in result)),
        ])
        return result
