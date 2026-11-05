"""Финальные дети узла rptg.check в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import cases as _m_cases

if TYPE_CHECKING:
    from rptg._types import CaseResult, CaseResults, ControlCase, Evidences, SelftestReport
    from rptg.check._types import CaseInput



class cases:
    """Лист rptg.check.cases: операции в обёртках условий."""

    @staticmethod
    def unpack(case: ControlCase) -> CaseInput:
        """вход контрольного случая → вход конвейера: полный вид {state, event} идёт как есть; вид ребра П3 {source_type, target_type, env} — в edges при пустых состоянии и событии"""
        result = _m_cases.unpack(case=case)
        return result

    @staticmethod
    def pick(case: ControlCase, evidences: Evidences) -> CaseResult:
        """вердикт проверки случая по доказательствам конвейера: провал любого — fail, иначе unknown любого — unknown, иначе pass; доказательств этой проверки нет — unknown"""
        result = _m_cases.pick(case=case, evidences=evidences)
        _c.check('rptg.check.cases:pick', 'ensures', [
            ('result.id == case.id', lambda: (result.id == case.id)),
            ('result.ok == (result.actual == result.expected)', lambda: (result.ok == (result.actual == result.expected))),
        ])
        return result

    @staticmethod
    def summarize(results: CaseResults) -> SelftestReport:
        """итоги контрольных случаев → сводка по проверкам в порядке слоёв"""
        _c.check('rptg.check.cases:summarize', 'requires', [
            ('len(results) >= 1', lambda: (len(results) >= 1)),
        ])
        result = _m_cases.summarize(results=results)
        _c.check('rptg.check.cases:summarize', 'ensures', [
            ('forall r in result.checks: r.trusted == (r.failed == 0)', lambda: all((r.trusted == (r.failed == 0)) for r in result.checks)),
            ('forall r in result.checks: r.passed + r.failed >= 1', lambda: all(((r.passed + r.failed) >= 1) for r in result.checks)),
        ])
        return result
