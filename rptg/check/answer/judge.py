"""Лист rptg.check.answer.judge — вердикт П1 (LOGIC §5).

Функции приняты по карточке design/rptg.check.answer.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Strings
    from rptg.check._types import ValidateJobs, Validations
    from rptg.check.answer._types import ClInfos, CondJobs


def form(answer: Answer, shape: ValidateJobs, checked: Validations, problems: Strings, conds: CondJobs,
         infos: ClInfos) -> Evidences:
    """Не карта и не разложение — пусто. Шаг split — unknown: это ограничение проверки, а не ошибка
    модели. Не извлечён — fail с причиной и пометкой обрыва. Не по схеме — fail со списком ошибок;
    нарушения имён и условия, которые не разобрались или не логические, — fail со списком. Иначе
    pass. Хэш — заглушка, его ставит verdict."""
    def one(verdict, details, tool):
        return [Evidence(check="P1", subject=answer.subject, subject_hash="0" * 64, hard=True, verdict=verdict,
                         details=details, tool=tool, trusted=False)]

    def cond_errors():
        return [f"{c.where} «{c.text}» — " + ("; ".join(i.errors) if not i.ok else f"не логическое ({i.type})")
                for c, i in zip(conds, infos) if not i.ok or i.type != "boolean"]

    if answer.kind in ("none", "function"):
        return []
    if answer.kind == "design_step" or not answer.ok:
        cut = {"truncated": True} if answer.truncated else {}
        return one("unknown" if answer.kind == "design_step" else "fail", {"reason": answer.error, **cut}, "extract")
    schema = [f"{job.where} — {e}" for job, v in zip(shape, checked) for e in v.errors]
    if schema:
        return one("fail", {"reason": "ответ не по схеме", "errors": schema}, "jsonschema")
    errors = list(problems) + cond_errors()
    if errors:
        return one("fail", {"reason": "условия или имена не проходят П1", "errors": errors}, "cl")
    return one("pass", {}, "jsonschema")
