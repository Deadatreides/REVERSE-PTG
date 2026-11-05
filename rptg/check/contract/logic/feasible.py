"""Лист rptg.check.contract.logic.feasible — выполнимость условий операций детей (LOGIC §5 П4, I14).

Функции приняты по карточке design/rptg.check.contract.logic.yaml; обвязку пишет скрипт.
Непустота — своя работа, отдельная от обязательств на рёбрах схем: у карты схем нет, а условия
операций корня проверить надо. Ответ сюда приходит прошедшим П1, состояние — записью
типизированного State.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import TypeEnv
from rptg.check.contract.logic._types import SatJob

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json
    from rptg.check.contract.logic._types import SatJobs


def jobs(state: Json, answer: Answer, form: Evidences) -> SatJobs:
    """Для каждой операции детей (у карты — корня): requires выполнимо; requires ∧ ensures выполнимо
    хотя бы при одном результате. Окружение — Decimal, Json, типы строгих предков и новые типы
    ответа, параметры, для второго задания — ещё result. Не карта и не разложение или П1 не
    прошла — пусто."""
    if answer.kind not in ("design", "map") or not form or form[0].verdict != "pass":
        return []
    value = answer.value

    def visible():
        found = {"Decimal": {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}, "Json": {}}
        if answer.kind == "design":
            parts = answer.node.split(".")
            owners = {".".join(parts[:i]) for i in range(1, len(parts))}
            found |= {n: t["schema"] for n, t in state["types"].items() if t["owner"] in owners}
        return found | {t["name"]: t["schema"] for t in value["types"]}

    types = visible()

    def of_op(card, op):
        params, where = {p["name"]: p["type"] for p in op["params"]}, f"{card['id']}:{op['name']}"
        out = []
        if op["requires"]:
            out.append(SatJob(details={"rule": "I14", "where": f"{where}: requires", "expected": "условия выполнимы"},
                              conds=op["requires"], env=TypeEnv(types=types, vars=params)))
        if op["ensures"]:
            out.append(SatJob(details={"rule": "I14", "where": f"{where}: requires ∧ ensures",
                                       "expected": "условия выполнимы хотя бы при одном результате"},
                              conds=op["requires"] + op["ensures"], env=TypeEnv(types=types, vars={**params, "result": op["result"]})))
        return out

    cards = value["children"] if answer.kind == "design" else [value["card"]]
    return [j for card in cards for op in card["ops"] for j in of_op(card, op)]
