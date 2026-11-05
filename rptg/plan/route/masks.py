"""Лист rptg.plan.route.masks — ручные назначения узла по маскам (LOGIC §6.6).

Функции приняты по карточке design/rptg.plan.route.yaml; обвязку пишет скрипт. Старшинство масок —
то же, что у предела Э1 в check.code.size: точный путь сильнее маски с большим числом буквальных
сегментов, та — уровня, при равенстве побеждает позднее в файле.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Override

if TYPE_CHECKING:
    from rptg._types import Config


def resolve(subject: str, cfg: Config) -> Override:
    """Узел — из предмета вид:узел[:операция] или сам путь; маски: точный путь, база.* — ровно один
    сегмент ниже базы, база.** — база и поддерево, level:a..b — уровни; ключи сливаются, заданные
    поздним перекрывают."""
    node = subject.split(":")[1] if ":" in subject else subject
    level = node.count(".") + 1
    keys = ("kind", "designer", "implementer", "start_rung", "max_rung", "approve", "steps", "est_lines", "max_lines",
            "max_complexity")

    def rank(mask):
        if mask.startswith("level:"):
            lo, _, hi = mask[len("level:"):].partition("..")
            return 0 if int(lo) <= level <= int(hi or lo) else -1
        base, _, tail = mask.rpartition(".")
        inside = {"**": node == base or node.startswith(base + "."),
                  "*": node.startswith(base + ".") and node.count(".") == base.count(".") + 1}
        return base.count(".") + 1 if inside.get(tail) else 1000 if mask == node else -1

    merged: dict = {}
    for _, _, ov in sorted((rank(mask), i, ov) for i, (mask, ov) in enumerate(cfg.overrides.items()) if rank(mask) >= 0):
        merged.update({k: getattr(ov, k) for k in keys if getattr(ov, k) is not None})
    return Override(**merged)
