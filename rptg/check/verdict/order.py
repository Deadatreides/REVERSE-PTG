"""Лист rptg.check.verdict.order — доказательства слоёв в одном списке.

Функции приняты по карточке design/rptg.check.verdict.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Config, Evidences, Sha
    from rptg.check._types import Parts, SubjectRef


def assemble(parts: Parts, subject: SubjectRef, digest: Sha, cfg: Config) -> Evidences:
    """Порядок P1 P2 P3 P4 P5 P7 E1 E2 E3 E6; после провала П1 остальные слои отбрасываются —
    проверять нечего. Каждому доказательству — предмет события, его хэш, HARD и доверие: проверка
    доверенная, если оболочка внесла её в cfg.trusted по итогу контрольных случаев."""
    order = ["P1", "P2", "P3", "P4", "P5", "P7", "E1", "E2", "E3", "E6"]
    found = parts.form + parts.structure + parts.data + parts.logic + parts.examples + parts.static + parts.runs
    if any(e.check == "P1" and e.verdict == "fail" for e in parts.form):
        found = [e for e in found if e.check == "P1"]
    trusted = set(cfg.trusted or [])
    out = [Evidence(check=e.check, subject=subject.subject, subject_hash=digest, hard=True, verdict=e.verdict,
                    details=e.details, counterexample=e.counterexample, tool=e.tool, trusted=e.check in trusted)
           for e in found]
    return sorted(out, key=lambda e: order.index(e.check))
