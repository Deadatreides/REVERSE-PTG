"""Лист rptg.check.answer.conds — условия из годного ответа с окружениями (LOGIC §5 П1, шаг 3).

Функции приняты по карточке design/rptg.check.answer.yaml; обвязку пишет скрипт. Ответ сюда
приходит только прошедшим схему метода, поэтому обязательные поля читаются напрямую.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import TypeEnv
from rptg.check.answer._types import CondJob

if TYPE_CHECKING:
    from rptg._types import Answer, Json
    from rptg.check._types import Validations
    from rptg.check.answer._types import CondJobs


def jobs(state: Json, answer: Answer, checked: Validations) -> CondJobs:
    """Разложение — условия операций детей, карта — операций корня. Видимые типы (§2.5) — Decimal,
    Json, типы строгих предков узла из состояния и новые типы ответа; у карты — её типы. Для
    гарантий в окружении ещё result. Ответ не прошёл схему — заданий нет: разбирать нечего."""
    if not checked or not all(v.ok for v in checked):
        return []
    value = answer.value

    def visible():
        found = {"Decimal": {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}, "Json": {}}
        if answer.kind == "design":
            parts = answer.node.split(".")
            owners = {".".join(parts[:i]) for i in range(1, len(parts))}
            found.update({n: t["schema"] for n, t in state["types"].items() if t["owner"] in owners})
        return {**found, **{t["name"]: t["schema"] for t in value["types"]}}

    types = visible()
    cards = value["children"] if answer.kind == "design" else [value["card"]]

    def of_op(card, op):
        params = {p["name"]: p["type"] for p in op["params"]}
        sides = [("requires", params), ("ensures", {**params, "result": op["result"]})]
        return [CondJob(where=f"{card['id']}:{op['name']} {side}[{i}]", text=text, env=TypeEnv(types=types, vars=names))
                for side, names in sides for i, text in enumerate(op[side])]

    return [job for card in cards for op in card["ops"] for job in of_op(card, op)]
