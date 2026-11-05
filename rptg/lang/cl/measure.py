"""Лист rptg.lang.cl.measure — меры условия для прикидки и рода работы (LOGIC §4.5, §6.3).

Функции приняты по карточке design/rptg.lang.cl.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl._types import ClMeasures

if TYPE_CHECKING:
    from rptg.lang.cl._types import ParseResult


def measure(parsed: ParseResult) -> ClMeasures:
    """Узлы, кванторы и агрегаты, нелинейность, есть ли арифметика и строки, свободные имена по алфавиту.

    Узел — каждый оператор, вызов, квантор, агрегат, путь и литерал; набор {…} — один литерал;
    переменная квантора отдельно не считается. Нелинейность — *, /, %, где оба операнда не числа.
    Строки — строковый литерал или startswith: len без типов не отличить от len списка.
    """
    out = {"nodes": 0, "quant": 0, "nonlin": 0, "arith": False, "strings": False}
    names: set = set()
    if not parsed.ok or parsed.ast is None:
        return ClMeasures(**out, names=[])

    def path(node, bound):
        if node.name not in bound:
            names.add(node.name)
        for s in node.steps:
            if s.idx is not None:
                walk(s.idx, bound)

    def flags(node, args):
        out["arith"] = out["arith"] or node.k in ("arith", "neg")
        if node.k == "arith" and node.op in ("*", "/", "%") and all(a.k != "num" for a in args):
            out["nonlin"] += 1
        literal = node.k == "str" or (node.k == "set" and any(a.k == "str" for a in args))
        out["strings"] = out["strings"] or literal or (node.k == "func" and node.name == "startswith")

    def walk(node, bound):
        args = node.args or []
        out["nodes"] += 1
        if node.k == "path":
            path(node, bound)
        elif node.k in ("quant", "agg"):
            out["quant"] += 1
            walk(args[0], bound)
            walk(args[1], bound | {node.name})
        else:
            flags(node, args)
            for a in args if node.k != "set" else []:
                walk(a, bound)

    walk(parsed.ast, frozenset())
    return ClMeasures(**out, names=sorted(names))
