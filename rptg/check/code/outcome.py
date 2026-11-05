"""Лист rptg.check.code.outcome — вердикт Э1 в ядре (LOGIC §5).

Функции приняты по карточке design/rptg.check.code.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Strings


def static(answer: Answer, rules: Strings, size: Strings) -> Evidences:
    """Ответ не функция — пусто; не извлечён — fail с причиной (функция — единственный блок python,
    LOGIC §8.3); нарушения правил или размера — fail со списком; иначе pass. Хэш — заглушка, его
    ставит verdict."""
    if answer.kind != "function":
        return []
    found = rules + size
    if not answer.ok:
        verdict, details = "fail", {"reason": answer.error}
    else:
        verdict = "fail" if found else "pass"
        details = {"rule": "E1", "where": answer.subject, "problems": found} if found else {}
    return [Evidence(check="E1", subject=answer.subject, subject_hash="0" * 64, hard=True, verdict=verdict,
                     details=details, tool="ast", trusted=False)]
