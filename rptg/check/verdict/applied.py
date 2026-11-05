"""Лист rptg.check.verdict.applied — ответ, применённый к состоянию, и предмет события.

Функции приняты по карточке design/rptg.check.verdict.yaml; обвязку пишет скрипт. Ответ ложится в
состояние так, как его положит plan после приёмки, — тогда хэш, посчитанный сейчас, совпадёт с
хэшем, который потом посчитает приёмка.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.check.verdict._types import Applied

if TYPE_CHECKING:
    from rptg._types import Answer, Json


def apply(state: Json, event: Json, answer: Answer) -> Applied:
    """Разложение — в designs[узел], его типы — в types; функция — в code[узел:операция]; карта —
    map_text, карточка корня и типы корня. Предмет — предмет ответа, у события без ответа модели —
    предмет цели прогона: цель в корне без вида, предмет — function: у тестов функции и assembly: у
    сборки (нет цели — пусто); ответ не извлечён — raw = его сырой текст, по нему и считается хэш."""
    if answer.kind == "none":
        target = event.get("target")
        if target is None:
            return Applied(state=state, subject="", raw=None)
        kind = "function:" if target["kind"] == "function_tests" else "assembly:"
        return Applied(state=state, subject=kind + target["subject"], raw=None)
    if not answer.ok:
        return Applied(state=state, subject=answer.subject, raw=event["answer"]["text"])
    value, new = answer.value, dict(state)
    if answer.kind == "function":
        new["code"] = {**state["code"], f"{answer.node}:{answer.op}": answer.code}
    else:
        new["types"] = {**state["types"], **{t["name"]: t for t in value["types"]}}
    if answer.kind == "design":
        new["designs"] = {**state["designs"], answer.node: value}
    if answer.kind == "map":
        new["map_text"], new["cards"] = value["map_text"], {**state["cards"], answer.node: value["card"]}
    return Applied(state=new, subject=answer.subject, raw=None)
