"""Лист rptg.check.graph.outcome — вердикт П2 (LOGIC §5).

Функции приняты по карточке design/rptg.check.graph.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Strings


def structure(answer: Answer, form: Evidences, tree: Strings, links: Strings) -> Evidences:
    """Неприменимо (не разложение или П1 не прошла) — пусто; нарушений нет — pass; иначе fail, в
    details — все нарушения, правило и место первого (строка «Iн: место: что»). Хэш — заглушка,
    его ставит verdict."""
    if answer.kind != "design" or not form or form[0].verdict != "pass":
        return []
    found = tree + links
    rule, _, rest = found[0].partition(": ") if found else ("", "", "")
    details = {"rule": rule, "where": rest.partition(": ")[0], "violations": found} if found else {}
    return [Evidence(check="P2", subject=answer.subject, subject_hash="0" * 64, hard=True,
                     verdict="fail" if found else "pass", details=details, tool="networkx", trusted=False)]
