"""Лист rptg.check.contract.data.subs — пары имён типов для подтипа (LOGIC §5 П3).

Функции приняты по карточке design/rptg.check.contract.data.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import TypeEnv
from rptg.check.contract.data._types import SubJob

if TYPE_CHECKING:
    from rptg.check.contract.data._types import EdgeJobs, PathTypes, SubJobs


def jobs(edges: EdgeJobs, paths: PathTypes) -> SubJobs:
    """Сторона ребра с путём — имя из итога пути; безымянная схема пути получает имя «·N» (N — номер
    пути) и ложится в окружение. Ребро с неразрешённым путём пропускается — его покажет вердикт.
    Затем прямые задания контрольных случаев."""
    extra = {f"·{i}": p.schema for i, p in enumerate(paths) if p.ok and not p.name}
    env = TypeEnv(types=edges.env.types | extra, vars={})

    def name(plain, at):
        if at < 0:
            return plain
        return (paths[at].name or f"·{at}") if paths[at].ok else None

    pairs = [(e.where, name(e.a, e.a_at), name(e.b, e.b_at)) for e in edges.edges]
    return [SubJob(where=w, a=a, b=b, env=env) for w, a, b in pairs if a is not None and b is not None] + edges.direct
