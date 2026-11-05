"""Лист rptg.check.contract.logic.equal — равенство значений по их типу для П4 (LOGIC §5 П4).

Функции приняты по карточке design/rptg.check.contract.logic.yaml; обвязку пишет скрипт. Отдельная от
развёртки схем работа (29.09.2026, вариант (а) пользователя): развёртка знает, что с чем равно —
поле записи с источником, выход свёртки с накопителем, — а этот лист знает, как равенство значений
записывается по их типу. Списки ограничены K = k_lists, как в Z3.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.check.contract.logic._types import FactPlan, OpPlan, Step

if TYPE_CHECKING:
    from rptg._types import Config


def expand(plan: FactPlan, cfg: Config) -> FactPlan:
    """Каждый шаг eq — факты left.p == right.p по скалярным путям схемы: у записи — обязательные
    поля (необязательные — в partial: равенство с отсутствующим значением фактом не записать), вглубь
    по вложенным записям; у списка — длина и элементы до k_lists под условием len(right) > i;
    словарь и непрозрачный Json — в partial. Условие шага сохраняется и сочетается с условиями
    элементов. Остальные шаги и поля плана не меняются."""
    k, partial = cfg.limits.k_lists, list(plan.partial)

    def of_op(op):
        types = op.env.types

        def resolve(s):
            for _ in range(8):  # кольцо псевдонимов не зациклит
                if not (isinstance(s, dict) and "$ref" in s):
                    break
                s = {"type": s["$ref"]} if s["$ref"] in ("string", "integer", "number", "boolean") else types.get(s["$ref"], {})
            return s if isinstance(s, dict) else {}

        def eqs(left, right, s, guard, depth=0):
            s = resolve(s)
            kind = s.get("type") if depth < 3 else None
            if kind == "array":
                out = [(f"len({left}) == len({right})", guard)]
                for i in range(k):
                    inner = " and ".join(filter(None, (f"len({right}) > {i}", guard)))
                    out += eqs(f"{left}[{i}]", f"{right}[{i}]", s.get("items", {}), inner, depth + 1)
                return out
            if kind == "object" and "properties" in s:
                need = set(s.get("required", []))
                partial.extend(f"{left}.{f}" for f in s["properties"] if f not in need)
                return [x for f, fs in s["properties"].items() if f in need for x in eqs(f"{left}.{f}", f"{right}.{f}", fs, guard, depth + 1)]
            if kind in (None, "object"):
                partial.append(left)
                return []
            return [(f"{left} == {right}", guard)]

        steps = []
        for step in op.steps:
            if step.kind != "eq":
                steps.append(step)
                continue
            found = eqs(step.details["left"], step.details["right"], step.details["schema"], step.guard)
            steps += [Step(kind="fact", text=text, subst={}, guard=guard, details={}) for text, guard in found]
        return OpPlan(op=op.op, env=op.env, steps=steps, keep=op.keep)

    ops = [of_op(op) for op in plan.ops]
    return FactPlan(applicable=plan.applicable, subject=plan.subject, p5=plan.p5, ops=ops, unknown=plan.unknown,
                    partial=sorted(set(partial)))
