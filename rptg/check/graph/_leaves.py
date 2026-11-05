"""Финальные дети узла rptg.check.graph в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.graph.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import tree as _m_tree
from . import links as _m_links
from . import outcome as _m_outcome
from . import reach as _m_reach
from . import impact as _m_impact

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json, Strings



class tree:
    """Лист rptg.check.graph.tree: операции в обёртках условий."""

    @staticmethod
    def check(state: Json, answer: Answer, form: Evidences, cfg: Config) -> Strings:
        """нарушения инвариантов дерева по разложению из ответа против карточки узла, состояния и пределов; строка — «Iн: место: что»; неприменимо (не разложение или П1 провалена) — пусто"""
        result = _m_tree.check(state=state, answer=answer, form=form, cfg=cfg)
        return result


class links:
    """Лист rptg.check.graph.links: операции в обёртках условий."""

    @staticmethod
    def check(state: Json, answer: Answer, form: Evidences) -> Strings:
        """нарушения связности схем разложения из ответа; строка — «Iн: схема, узел: что»; неприменимо — пусто"""
        result = _m_links.check(state=state, answer=answer, form=form)
        return result


class outcome:
    """Лист rptg.check.graph.outcome: операции в обёртках условий."""

    @staticmethod
    def structure(answer: Answer, form: Evidences, tree: Strings, links: Strings) -> Evidences:
        """неприменимо — пусто; нарушений нет — pass; иначе fail, в details — все нарушения, правило и место первого"""
        result = _m_outcome.structure(answer=answer, form=form, tree=tree, links=links)
        _c.check('rptg.check.graph.outcome:structure', 'ensures', [
            ('len(result) <= 1', lambda: (len(result) <= 1)),
            ('forall e in result: e.check == "P2"', lambda: all((e.check == "P2") for e in result)),
        ])
        return result


class reach:
    """Лист rptg.check.graph.reach: операции в обёртках условий."""

    @staticmethod
    def dead_ops(state: Json) -> Strings:
        """операции всех карточек, до которых не доходит ни один вызов от операций корня, по порядку; корень — карточка без родителя"""
        result = _m_reach.dead_ops(state=state)
        return result


class impact:
    """Лист rptg.check.graph.impact: операции в обёртках условий."""

    @staticmethod
    def stale(state: Json, changed: Strings) -> Strings:
        """для каждого изменённого узла X: разложения, чьи схемы вызывают X (родитель и узлы с X в uses), разложение X, функции X, если он финальный, сборки X и всех предков; у устаревшего разложения — ещё его сборка и сборки предков; по порядку"""
        result = _m_impact.stale(state=state, changed=changed)
        return result
