"""Лист rptg.lang.cl.logic.decode — ответ решателя → вердикт метода и контрпример по путям CL.

Функции приняты по карточке design/rptg.lang.cl.logic.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Proof, Sat

if TYPE_CHECKING:
    from rptg._types import Limits
    from rptg.lang.cl.logic._types import SmtText, SolveResult


def proof(answer: SolveResult, smt: SmtText, limits: Limits) -> Proof:
    """unsat → доказано; sat → опровергнуто, контрпример — значения всех символов модели; иначе неизвестно.

    Символы и цели, и фактов: у обязательства П4 цель записана через выходы схемы, а значения
    параметров операции, которые нужны отчёту, есть только в фактах (LOGIC §5 П4).

    Целые становятся числами, логические — true/false, вещественные и строки остаются текстом:
    дробь 1/3 в JSON без потерь не записать.
    """
    bound = limits.k_lists
    if answer.status == "unsat":
        return Proof(verdict="proved", bound=bound)
    if answer.status != "sat":
        return Proof(verdict="unknown", bound=bound)
    example: dict = {}
    for sym in sorted(smt.kinds):
        if sym not in answer.model:
            continue
        text, sort = answer.model[sym], smt.kinds.get(sym)
        if sort == "Int" and text.lstrip("-").isdigit():
            example[sym] = int(text)
        elif sort == "Bool":
            example[sym] = text == "true"
        else:
            example[sym] = text
    return Proof(verdict="refuted", counterexample=example, bound=bound)


def sat(answer: SolveResult, smt: SmtText) -> Sat:
    """sat → выполнимо; unsat → номера строк ядра; иначе неизвестно.

    Невыполнимость без строк в ядре значит, что противоречат сами типы (например, minItems больше
    K), а не условия: вердикт тогда «неизвестно», виноватых строк нет.
    """
    if answer.status == "sat":
        return Sat(verdict="sat", core=[])
    core = sorted(int(name[1:]) for name in answer.core if name[:1] == "c" and name[1:].isdigit())
    if answer.status == "unsat" and core:
        return Sat(verdict="unsat", core=core)
    return Sat(verdict="unknown", core=[])
