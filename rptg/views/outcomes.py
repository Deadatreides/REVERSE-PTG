"""Лист rptg.views.outcomes — исходы рабочих прогонов по роду и оператору (LOGIC §6.8, ARCHITECTURE §7).

Функция принята по карточке design/rptg.views.yaml; обвязку пишет скрипт. Таблицы компетенций в State
нет — её держит оболочка; здесь только исходы, и они помечены «не для сравнения операторов»: на старшие
ступени доходят лишь трудные задачи. Цены — десятичные записи: модуль decimal узлу не разрешён, сумма — в
целых с масштабом самой длинной записи.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json


def rows(state: Json) -> Json:
    """Пометка «не для сравнения операторов» и строки по (род, оператор) назначения элементов в порядке
    рода и оператора: задач, принято, попыток, токенов, цена — сумма записей в масштабе самой длинной;
    элементы без назначения не считаются."""
    groups: dict = {}
    for e in state["elements"].values():
        a = e.get("assignment")
        if a:
            g = groups.setdefault((a["class"], a["operator"]), {"tasks": 0, "accepted": 0, "attempts": 0, "tokens": 0, "costs": []})
            g["tasks"], g["accepted"] = g["tasks"] + 1, g["accepted"] + int(e["state"] == "accepted")
            g["attempts"], g["tokens"] = g["attempts"] + e["attempts"], g["tokens"] + e.get("tokens", 0)
            g["costs"].append(e.get("cost", "0"))

    def total(costs):
        parsed = [(whole + frac, len(frac)) for whole, _, frac in (c.partition(".") for c in costs)]
        scale = max(s for _, s in parsed)
        digits = str(sum(int(d) * 10 ** (scale - s) for d, s in parsed)).rjust(scale + 1, "0")
        return digits[:-scale] + "." + digits[-scale:] if scale else digits

    note = ("исходы рабочих прогонов — не для сравнения операторов: на старшие ступени доходят только трудные задачи "
            "(LOGIC §6.8); операторов сравнивает калибровка")
    return {"note": note, "rows": [{"class": work, "operator": operator, "tasks": g["tasks"], "accepted": g["accepted"],
                                    "attempts": g["attempts"], "tokens": g["tokens"], "cost": total(g["costs"])}
                                   for (work, operator), g in sorted(groups.items())]}
