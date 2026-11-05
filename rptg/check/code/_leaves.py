"""Финальные дети узла rptg.check.code в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.code.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import rules as _m_rules
from . import size as _m_size
from . import outcome as _m_outcome
from . import runs as _m_runs

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json, Strings



class rules:
    """Лист rptg.check.code.rules: операции в обёртках условий."""

    @staticmethod
    def check(state: Json, answer: Answer) -> Strings:
        """нарушения правил по коду из ответа функции против карточки её узла; модуль — документация, импорты и один def операции; импорты — allowed_imports узла, typing, __future__ и сгенерированные типы проекта; open — только с эффектом fs.*; ответ не функция или не извлечён — пусто"""
        result = _m_rules.check(state=state, answer=answer)
        return result


class size:
    """Лист rptg.check.code.size: операции в обёртках условий."""

    @staticmethod
    def check(state: Json, answer: Answer, cfg: Config) -> Strings:
        """строки кода без документации, комментариев и пустых ≤ 2·D_код + S + 10; при объявленном D ещё D_код ≤ 1,5·D + 5; ручной max_lines узла — по физическим строкам; сложность блока ≤ max_complexity (ручное назначение узла сильнее предела проекта); договор — cfg.contracts[узел:операция]; ответ не функция или не извлечён — пусто"""
        result = _m_size.check(state=state, answer=answer, cfg=cfg)
        return result


class outcome:
    """Лист rptg.check.code.outcome: операции в обёртках условий."""

    @staticmethod
    def static(answer: Answer, rules: Strings, size: Strings) -> Evidences:
        """ответ не функция — пусто; не извлечён — fail с причиной; нарушения правил или размера — fail со списком; иначе pass. Хэш — заглушка, его ставит verdict"""
        result = _m_outcome.static(answer=answer, rules=rules, size=size)
        _c.check('rptg.check.code.outcome:static', 'ensures', [
            ('len(result) <= 1', lambda: (len(result) <= 1)),
            ('forall e in result: e.check == "E1"', lambda: all((e.check == "E1") for e in result)),
        ])
        return result


class runs:
    """Лист rptg.check.code.runs: операции в обёртках условий."""

    @staticmethod
    def read(state: Json, event: Json, cfg: Config) -> Evidences:
        """событие не прогон — пусто; mypy — Э1; у функции примеры — Э2, свойства — Э3 (мало годных входов — unknown); у сборки примеры и свойства вместе — Э6, виновный — по первому нарушению трассы; отчёта нет: тайм-аут — fail, иначе unknown"""
        result = _m_runs.read(state=state, event=event, cfg=cfg)
        _c.check('rptg.check.code.runs:read', 'ensures', [
            ('forall e in result: e.check == "E1" or e.check == "E2" or e.check == "E3" or e.check == "E6"', lambda: all(((((e.check == "E1") or (e.check == "E2")) or (e.check == "E3")) or (e.check == "E6")) for e in result)),
        ])
        return result
