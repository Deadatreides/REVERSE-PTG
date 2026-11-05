"""Лист rptg.lang.cl.strategy.bounds — границы из требований для стратегий Hypothesis.

Функции приняты по карточке design/rptg.lang.cl.strategy.yaml; обвязку пишет скрипт. С 30.09.2026
граница — у пути, а не только у параметра: свойства сборок (Э6) иначе тонули в фильтре, когда
условия лежали на полях и на элементах списка под forall.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl.strategy._types import Bound

if TYPE_CHECKING:
    from rptg.lang.cl._types import Typeds
    from rptg.lang.cl.strategy._types import Bounds


def bounds(requires: Typeds) -> Bounds:
    """Сравнения в конъюнкции требований → самые тесные границы по порядку: путь, что, сначала min.

    Путь — параметр и его поля через точку, элемент списка — []: x > 0 → x min 1, len(s) < 5 → s
    size max 4, 2 < x читается как x > 2. Под forall l in order.lines сравнения тела — о каждом
    элементе: l.qty > 0 → order.lines[].qty min 1. У нецелого пути строгое сравнение даёт
    нестрогую границу (price > 0 → min 0): исключённую точку отсекает фильтр. Путь с индексом,
    exists, импликация и прочее границами не становятся — их проверяет фильтр теста.
    """
    flip = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
    best: dict = {}

    def conjuncts(n, scope):
        if n.k == "and":
            return conjuncts(n.args[0], scope) + conjuncts(n.args[1], scope)
        if n.k == "quant" and n.op == "forall" and (over := target(n.args[0], scope)) is not None:
            return conjuncts(n.args[1], {**scope, n.name: over[0] + "[]"})
        return [(n, scope)]

    def target(n, scope):
        what = "value"
        if n.k == "func" and n.name == "len":
            n, what = n.args[0], "size"
        if n.k != "path":
            return None
        names = [s.attr for s in n.steps]
        return None if None in names else (".".join([scope.get(n.name, n.name)] + names), what)

    def take(c, scope, paths):
        if c.k != "cmp" or c.op not in flip:
            return
        (a, b), op = c.args, c.op
        if a.k == "num":
            a, b, op = b, a, flip[op]
        at = target(a, scope)
        if b.k != "num" or type(b.v) is not int or at is None:
            return
        step = op in ("<", ">") and (at[1] == "size" or paths.get(at[0]) in ("integer", "opt:integer"))
        side, v = ("min", b.v + step) if op in (">", ">=") else ("max", b.v - step)
        key = at + (side,)
        old = best.get(key, v)
        best[key] = max(old, v) if side == "min" else min(old, v)

    for t in requires:
        for c, scope in conjuncts(t.ast, {}) if t.ok and t.ast is not None else []:
            take(c, scope, t.paths)
    order = sorted(best, key=lambda k: (k[0], k[1], k[2] != "min"))
    return [Bound(name=k[0], what=k[1], side=k[2], v=best[k]) for k in order]
