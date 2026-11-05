"""Лист rptg.check.contract.logic.render — подстановка в условия CL и задания решателю (LOGIC §5 П4).

Функции приняты по карточке design/rptg.check.contract.logic.yaml; обвязку пишет скрипт. Обязательство
П4 — requires(C)[параметры ↦ источники]: подстановка идёт по словам текста условия. Переменная
квантора не бывает параметром (П1 это запрещает) и получает своё имя q__v, так что выражение
источника её не заденет.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rptg.check.contract.logic._types import Obligations, ProofJob

if TYPE_CHECKING:
    from rptg.check.contract.logic._types import FactPlan


def obligations(plan: FactPlan) -> Obligations:
    """В тексте шага слово — не в строке и не после точки — заменяется: переменная квантора на q__v,
    параметр — своим выражением. Шаг с условием — «(guard) => (текст)». Обязательство и цель П5
    получают факты всех шагов-фактов выше себя в своей операции; в details обязательства —
    obligation, его текст без условия шага."""
    proofs, refines = [], []

    def text(step):
        bound = set(re.findall(r"\b(?:forall|exists)\s+([A-Za-z_]\w*)\s+in\b", step.text))

        def swap(m):
            word = m.group(0)
            if word[0] == '"' or step.text[:m.start()].rstrip().endswith("."):
                return word
            return "q__" + word if word in bound else step.subst.get(word, word)

        return re.sub(r'"(?:[^"\\]|\\.)*"|[A-Za-z_]\w*', swap, step.text)

    for op in plan.ops:
        facts: list = []
        for step in op.steps:
            body = text(step)
            full = f"({step.guard}) => ({body})" if step.guard else body
            if step.kind == "fact":
                facts.append(full)
                continue
            details = {**step.details, "obligation": body} if step.kind == "goal" else step.details
            (proofs if step.kind == "goal" else refines).append(
                ProofJob(details=details, facts=list(facts), goal=full, env=op.env, keep=op.keep))
    return Obligations(applicable=plan.applicable, subject=plan.subject, p5=plan.p5, proofs=proofs, refines=refines,
                       unknown=plan.unknown, partial=plan.partial)
