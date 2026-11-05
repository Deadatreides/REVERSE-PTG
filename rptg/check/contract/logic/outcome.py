"""Лист rptg.check.contract.logic.outcome — вердикты П4 и П5 по итогам решателя (LOGIC §5 П4).

Функции приняты по карточке design/rptg.check.contract.logic.yaml; обвязку пишет скрипт. Хэш —
заглушка, его ставит verdict.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Evidences
    from rptg.check.contract.logic._types import Obligations, Proofs, SatJobs, Sats


def verdict(obligations: Obligations, proofs: Proofs, empties: SatJobs, sats: Sats, refines: Proofs) -> Evidences:
    """Неприменимо — пусто. П4: невыполнимые условия — fail с противоречивым набором строк (I14): при
    противоречии любое обязательство ниже бессмысленно, поэтому I14 называется первым; иначе
    опровергнутое обязательство — fail с его details и контрпримером по путям параметров операции,
    но unknown, если контрпример задевает путь с неполными фактами (он может быть ложным); unknown
    решателя или невыраженное планом — unknown; иначе pass. П5 — так же по целям, если p5."""
    if not obligations.applicable:
        return []

    def head(key):
        return re.split(r"[.\[]", key[4:-1] if key.startswith("len(") else key, maxsplit=1)[0]

    def partial(example):
        return any(k.startswith(p) or k.startswith(f"len({p}") for k in example for p in obligations.partial)

    def judged(jobs, found, extra_unknown):
        refuted = [(j, r) for j, r in zip(jobs, found) if r.verdict == "refuted"]
        unsure = extra_unknown or any(r.verdict == "unknown" for r in found)
        if not refuted:
            return ("unknown" if unsure else "pass"), {}, None
        job, r = refuted[0]
        kept = {k: v for k, v in (r.counterexample or {}).items() if head(k) in job.keep}
        return ("unknown" if partial(r.counterexample or {}) else "fail"), job.details, kept

    def one(check, found):
        v, details, counter = found
        return Evidence(check=check, subject=obligations.subject, subject_hash="0" * 64, hard=True, verdict=v,
                        details=details, counterexample=counter, tool="z3", trusted=False)

    empty = [(s, r) for s, r in zip(empties, sats) if r.verdict == "unsat"]
    p4 = judged(obligations.proofs, proofs, bool(obligations.unknown) or any(r.verdict == "unknown" for r in sats))
    if empty:
        job, r = empty[0]
        p4 = ("fail", {**job.details, "core": [job.conds[i] for i in r.core]}, None)
    out = [one("P4", p4)]
    return out + ([one("P5", judged(obligations.refines, refines, False))] if obligations.p5 else [])
