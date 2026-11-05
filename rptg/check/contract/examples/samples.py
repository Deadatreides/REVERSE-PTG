"""Лист rptg.check.contract.examples.samples — задания П7 по примерам операций (LOGIC §5 П7, I15, I16).

Функции приняты по карточке design/rptg.check.contract.examples.yaml; обвязку пишет скрипт. Ответ сюда
приходит прошедшим П1, состояние — записью типизированного State.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import TypeEnv
from rptg.check._types import ValidateJob
from rptg.check.contract.examples._types import EvalJob, SampleJobs

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json


def jobs(state: Json, answer: Answer, form: Evidences) -> SampleJobs:
    """Для каждого примера операций детей (у карты — корня), включая примеры пользователя: вход — по
    типам параметров, выход точного примера — по типу результата; requires на входе; ensures на
    входе и result = out — только у точного примера (у примера по подмножеству выход неполон, его
    гарантии проверит Э2). Без языка: примеров меньше I15 (у корня ≥ 2 и хотя бы один
    пользователя), пример пользователя не вошёл в карточку, вход не по параметрам, «*» в точном
    примере."""
    if answer.kind not in ("design", "map") or not form or form[0].verdict != "pass":
        return SampleJobs(applicable=False, subject=answer.subject, validations=[], evals=[], problems=[])
    value, root = answer.value, answer.kind == "map"

    def visible():
        found = {"Decimal": {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}, "Json": {}}
        if not root:
            parts = answer.node.split(".")
            owners = {".".join(parts[:i]) for i in range(1, len(parts))}
            found |= {n: t["schema"] for n, t in state["types"].items() if t["owner"] in owners}
        return found | {t["name"]: t["schema"] for t in value["types"]}

    types = visible()
    validations: list = []
    evals: list = []

    def starred(v):
        if isinstance(v, dict):
            return any(starred(x) for x in v.values())
        return any(starred(x) for x in v) if isinstance(v, list) else v == "*"

    def counted(key, op, users):
        need = 2 if root else 1
        out = [f"I15: {key}: примеров {len(op['examples'])}, нужно не меньше {need}"] if len(op["examples"]) < need else []
        out += [f"I15: {key}: нет примера пользователя"] if root and not any(e["source"] == "user" for e in op["examples"]) else []
        return out + [f"I17: {key}: пример пользователя {i} не вошёл в карточку" for i, e in enumerate(users, 1) if e not in op["examples"]]

    def of_example(where, op, ex):
        params = {p["name"]: p["type"] for p in op["params"]}
        if not isinstance(ex["in"], dict) or set(ex["in"]) != set(params):
            return [f"I16: {where}: вход не совпадает с параметрами {sorted(params)}"]
        exact, given = ex.get("match", "exact") == "exact", TypeEnv(types=types, vars=params)
        validations.extend(ValidateJob(where=f"{where}: in.{p}", value=ex["in"][p], type=t, env=given) for p, t in params.items())
        evals.extend(EvalJob(where=f"{where}: requires «{c}»", text=c, env=given, values=ex["in"]) for c in op["requires"])
        if not exact:
            return []
        validations.append(ValidateJob(where=f"{where}: out", value=ex["out"], type=op["result"], env=given))
        after = TypeEnv(types=types, vars={**params, "result": op["result"]})
        evals.extend(EvalJob(where=f"{where}: ensures «{c}»", text=c, env=after, values={**ex["in"], "result": ex["out"]})
                     for c in op["ensures"])
        return [f"I16: {where}: «*» разрешена только в примере по подмножеству"] if starred(ex["out"]) else []

    def of_op(card, op):
        key = f"{card['id']}:{op['name']}"
        users = state["user_examples"].get(key, [])
        examples = op["examples"] + [e for e in users if e not in op["examples"]]
        return counted(key, op, users) + [p for i, ex in enumerate(examples, 1) for p in of_example(f"{key} пример {i}", op, ex)]

    problems = [p for card in (value["children"] if not root else [value["card"]]) for op in card["ops"] for p in of_op(card, op)]
    return SampleJobs(applicable=True, subject=answer.subject, validations=validations, evals=evals, problems=problems)
