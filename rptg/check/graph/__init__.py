"""П2 и граф проекта: инварианты дерева и схем потоков (I1–I9, I11, I17, I18), мёртвые операции (I10), устаревание (LOGIC §7.7)

Сгенерировано tools/codegen0.py по design/rptg.check.graph.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json, Strings



def structure(state: Json, answer: Answer, form: Evidences, cfg: Config) -> Evidences:
    """П2 по разложению из ответа против карточки узла и состояния; если ответ не разложение или П1 провалена — пусто"""
    result = _flows.structure(state=state, answer=answer, form=form, cfg=cfg)
    _c.check('rptg.check.graph:structure', 'ensures', [
        ('len(result) <= 1', lambda: (len(result) <= 1)),
        ('forall e in result: e.check == "P2"', lambda: all((e.check == "P2") for e in result)),
    ])
    return result


def dead_ops(state: Json) -> Strings:
    """операции, недостижимые от операций корня по схемам потоков (I10), по порядку"""
    result = _flows.dead_ops(state=state)
    return result


def stale(state: Json, changed: Strings) -> Strings:
    """что устаревает, когда изменились карточки узлов (LOGIC §7.7): вызывающие разложения, разложение узла, функции узла, сборки узла и предков, по порядку"""
    result = _flows.stale(state=state, changed=changed)
    return result
