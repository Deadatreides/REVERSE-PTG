"""Лист rptg.check.contract.examples.outcome — вердикт П7 по итогам языка (LOGIC §5 П7).

Функции приняты по карточке design/rptg.check.contract.examples.yaml; обвязку пишет скрипт. Хэш —
заглушка, его ставит verdict.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Evidences
    from rptg.check._types import Validations
    from rptg.check.contract.examples._types import EvalResults, SampleJobs


def verdict(jobs: SampleJobs, validations: Validations, evals: EvalResults) -> Evidences:
    """Неприменимо — пусто. Значение не по типу, условие ложно или не вычисляется, нарушения без
    языка — fail; в details правило первого нарушения (I15 — число примеров, I16 — пример, I17 —
    потерянный пример пользователя), его место и все нарушения. Иначе pass."""
    if not jobs.applicable:
        return []
    bad = [(p.split(": ")[0], p.split(": ")[1], p) for p in jobs.problems]
    bad += [("I16", j.where, f"{j.where}: значение не по типу {j.type} — {'; '.join(v.errors)}")
            for j, v in zip(jobs.validations, validations) if not v.ok]
    bad += [("I16", j.where, f"{j.where}: " + ("ложно" if r.ok else f"не вычисляется — {r.error}"))
            for j, r in zip(jobs.evals, evals) if not r.ok or not r.value]
    details = {"rule": bad[0][0], "where": bad[0][1], "violations": [m for _, _, m in bad]} if bad else {}
    return [Evidence(check="P7", subject=jobs.subject, subject_hash="0" * 64, hard=True, verdict="fail" if bad else "pass",
                     details=details, tool="cl", trusted=False)]
