"""Лист rptg.check.contract.data.outcome — вердикт П3 по итогам языка (LOGIC §5 П3, I12).

Функции приняты по карточке design/rptg.check.contract.data.yaml; обвязку пишет скрипт. Хэш —
заглушка, его ставит verdict.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Evidence

if TYPE_CHECKING:
    from rptg._types import Evidences
    from rptg.check._types import Validations
    from rptg.check.contract.data._types import EdgeJobs, PathTypes, SubJobs, SubResults


def verdict(edges: EdgeJobs, paths: PathTypes, consts: Validations, subs: SubJobs, results: SubResults) -> Evidences:
    """Неприменимо — пусто. Неразрешённый путь, литерал не по типу места, не подтип (со свидетелем —
    значением, которое проходит схему источника и не проходит схему назначения) — fail; в details
    правило I12, место первого нарушения и все нарушения. Иначе pass."""
    def violations():
        out = [(e.where, f"{e.where}: путь {edges.paths[at].root}.{edges.paths[at].path} не разрешён — {paths[at].error}")
               for e in edges.edges for at in (e.a_at, e.b_at) if at >= 0 and not paths[at].ok]
        out += [(j.where, f"{j.where}: литерал не по типу {j.type} — {'; '.join(v.errors)}")
                for j, v in zip(edges.consts, consts) if not v.ok]
        return out + [(s.where, f"{s.where}: {s.a} не подтип {s.b}" + (f", свидетель {r.witness!r}" if r.witness is not None else ""))
                      for s, r in zip(subs, results) if not r.ok]

    if not edges.applicable:
        return []
    bad = violations()
    details = {"rule": "I12", "where": bad[0][0], "violations": [m for _, m in bad]} if bad else {}
    return [Evidence(check="P3", subject=edges.subject, subject_hash="0" * 64, hard=True, verdict="fail" if bad else "pass",
                     details=details, tool="lang", trusted=False)]
