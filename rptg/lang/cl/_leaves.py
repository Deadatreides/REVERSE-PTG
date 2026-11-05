"""Финальные дети узла rptg.lang.cl в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.yaml — не править руками.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import parse as _m_parse
from . import typecheck as _m_typecheck
from . import measure as _m_measure
from . import evaluate as _m_evaluate
from . import python as _m_python

if TYPE_CHECKING:
    from rptg._types import Cl, EvalResult, Json, TypeEnv
    from rptg.lang.cl._types import ClMeasures, ParseResult, Typed



class parse:
    """Лист rptg.lang.cl.parse: операции в обёртках условий."""

    @staticmethod
    def parse(text: Cl) -> ParseResult:
        """разбор с ошибками по позиции; имя поля после точки может быть служебным словом"""
        result = _m_parse.parse(text=text)
        _c.check('rptg.lang.cl.parse:parse', 'ensures', [
            ('result.ok => result.ast != null', lambda: ((not result.ok) or (result.ast is not None))),
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
            ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
        ])
        return result


class typecheck:
    """Лист rptg.lang.cl.typecheck: операции в обёртках условий."""

    @staticmethod
    def typecheck(parsed: ParseResult, env: TypeEnv) -> Typed:
        """проверить типы; необязательное значение — только под != null в той же конъюнкции или посылке"""
        result = _m_typecheck.typecheck(parsed=parsed, env=env)
        _c.check('rptg.lang.cl.typecheck:typecheck', 'ensures', [
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
            ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
            ('not parsed.ok => not result.ok', lambda: ((not (not parsed.ok)) or (not result.ok))),
        ])
        return result


class measure:
    """Лист rptg.lang.cl.measure: операции в обёртках условий."""

    @staticmethod
    def measure(parsed: ParseResult) -> ClMeasures:
        """узлы, кванторы и агрегаты, нелинейность, есть ли арифметика и строки, свободные имена по алфавиту"""
        result = _m_measure.measure(parsed=parsed)
        _c.check('rptg.lang.cl.measure:measure', 'ensures', [
            ('result.nodes >= 0', lambda: (result.nodes >= 0)),
        ])
        return result


class evaluate:
    """Лист rptg.lang.cl.evaluate: операции в обёртках условий."""

    @staticmethod
    def evaluate(typed: Typed, values: Json) -> EvalResult:
        """десятичные — по видам путей; деление на ноль даёт ложь"""
        result = _m_evaluate.evaluate(typed=typed, values=values)
        _c.check('rptg.lang.cl.evaluate:evaluate', 'ensures', [
            ('result.ok => result.error == null', lambda: ((not result.ok) or (result.error is None))),
        ])
        return result


class python:
    """Лист rptg.lang.cl.python: операции в обёртках условий."""

    @staticmethod
    def python(typed: Typed) -> str:
        """каждая бинарная операция в скобках; квантор — all/any; десятичный литерал — Decimal('…')"""
        result = _m_python.python(typed=typed)
        _c.check('rptg.lang.cl.python:python', 'ensures', [
            ('len(result) >= 1', lambda: (len(result) >= 1)),
        ])
        return result
