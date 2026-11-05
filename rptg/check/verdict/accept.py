"""Лист rptg.check.verdict.accept — правило приёмки (LOGIC §10).

Функции приняты по карточке design/rptg.check.verdict.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Acceptance

if TYPE_CHECKING:
    from rptg._types import Json, Sha
    from rptg.check.verdict._types import Needed, Shas


def judge(state: Json, needed: Needed, main: Sha, more: Shas) -> Acceptance:
    """Слой есть, если на текущем хэше предмета есть HARD pass доверенной проверки и нет HARD fail
    или unknown: проверки детерминированы, и провал на том же хэше не перекрыть проходом (так
    статика Э1 и mypy дают по доказательству на один хэш). missing — недостающие слои предмета и
    всех предметов more, в порядке слоёв без повторов."""
    required = {"design": ["P1", "P2", "P3", "P4", "P7"], "function": ["E1", "E2", "E3"],
                "assembly": ["E6"], "map": ["P1", "P4", "P7"]}
    order = ["P1", "P2", "P3", "P4", "P5", "P7", "E1", "E2", "E3", "E6"]

    def lacks(subject, digest):
        mine = [e for e in state["evidence"].get(subject, []) if e["subject_hash"] == digest and e["hard"]]
        passed = {e["check"] for e in mine if e["verdict"] == "pass" and e["trusted"]}
        spoiled = {e["check"] for e in mine if e["verdict"] != "pass"}
        return [c for c in required[subject.partition(":")[0]] if c not in passed or c in spoiled]

    pairs = [(needed.main, main)] + list(zip(needed.more, more))
    missing = {c for ref, digest in pairs for c in lacks(ref.subject, digest)}
    return Acceptance(accepted=not missing, missing=sorted(missing, key=order.index))
