"""Финальные дети узла rptg.check.contract.data в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.data.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import edges as _m_edges
from . import subs as _m_subs
from . import outcome as _m_outcome

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json
    from rptg.check._types import Validations
    from rptg.check.contract.data._types import EdgeJobs, PathTypes, SubJobs, SubResults



class edges:
    """Лист rptg.check.contract.data.edges: операции в обёртках условий."""

    @staticmethod
    def jobs(state: Json, answer: Answer, form: Evidences, edges: Json) -> EdgeJobs:
        """по схемам операций узла: путь от параметра или выхода узла схемы — задание пути, имя типа — как есть; элемент отображения и свёртки — путь по [0]; литерал — задание проверки по типу места; рёбра из edges — прямые задания подтипа; окружение — Decimal, Json, типы строгих предков и новые типы; неприменимо — applicable: false"""
        result = _m_edges.jobs(state=state, answer=answer, form=form, edges=edges)
        _c.check('rptg.check.contract.data.edges:jobs', 'ensures', [
            ('forall e in result.edges: e.a_at < len(result.paths) and e.b_at < len(result.paths)', lambda: all(((e.a_at < len(result.paths)) and (e.b_at < len(result.paths))) for e in result.edges)),
        ])
        return result


class subs:
    """Лист rptg.check.contract.data.subs: операции в обёртках условий."""

    @staticmethod
    def jobs(edges: EdgeJobs, paths: PathTypes) -> SubJobs:
        """для ребра: сторона с путём — имя из итога пути или новое «·N» (N — номер пути) со схемой пути в окружении; неразрешённый путь — ребро пропускается (его покажет вердикт); затем прямые задания"""
        _c.check('rptg.check.contract.data.subs:jobs', 'requires', [
            ('len(paths) == len(edges.paths)', lambda: (len(paths) == len(edges.paths))),
        ])
        result = _m_subs.jobs(edges=edges, paths=paths)
        return result


class outcome:
    """Лист rptg.check.contract.data.outcome: операции в обёртках условий."""

    @staticmethod
    def verdict(edges: EdgeJobs, paths: PathTypes, consts: Validations, subs: SubJobs, results: SubResults) -> Evidences:
        """неприменимо — пусто; неразрешённый путь, литерал не по типу, не подтип (со свидетелем) — fail, в details правило I12, место и все нарушения; иначе pass"""
        _c.check('rptg.check.contract.data.outcome:verdict', 'requires', [
            ('len(paths) == len(edges.paths)', lambda: (len(paths) == len(edges.paths))),
            ('len(consts) == len(edges.consts)', lambda: (len(consts) == len(edges.consts))),
            ('len(results) == len(subs)', lambda: (len(results) == len(subs))),
        ])
        result = _m_outcome.verdict(edges=edges, paths=paths, consts=consts, subs=subs, results=results)
        _c.check('rptg.check.contract.data.outcome:verdict', 'ensures', [
            ('len(result) <= 1', lambda: (len(result) <= 1)),
            ('forall e in result: e.check == "P3"', lambda: all((e.check == "P3") for e in result)),
        ])
        return result
