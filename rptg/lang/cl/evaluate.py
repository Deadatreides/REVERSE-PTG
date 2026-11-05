"""Лист rptg.lang.cl.evaluate — вычисление условия на данных обходом дерева, без eval.

Функции приняты по карточке design/rptg.lang.cl.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from rptg._types import EvalResult

if TYPE_CHECKING:
    from rptg._types import Json
    from rptg.lang.cl._types import Typed


def evaluate(typed: Typed, values: Json) -> EvalResult:
    """Десятичные — по видам путей; деление на ноль даёт ложь.

    Целые остаются целыми, дробные числа JSON и строки вида decimal становятся Decimal, поэтому
    0.1 + 0.2 == 0.3 истинно — как в Z3, а не как во float. Деление — точное до 28 знаков.
    Ошибка на данных (нет значения, поле у null, индекс вне списка) — ok: false с причиной.
    Данные — JSON, как в примерах карточек; дерево условия — объекты.
    """
    if not typed.ok or typed.ast is None:
        return EvalResult(ok=False, value=False, error="; ".join(typed.errors) or "условие не типизировано")
    kinds = typed.paths

    class Bad(Exception):
        pass

    class DivZero(Exception):
        pass

    def truth(v):
        if not isinstance(v, bool):
            raise Bad(f"не логическое значение: {v!r}")
        return v

    def number(v):
        if isinstance(v, bool) or not isinstance(v, (int, Decimal)):
            raise Bad(f"не число: {v!r}")
        return v

    def read(v, norm):
        if isinstance(v, float):
            return Decimal(repr(v))
        if isinstance(v, str) and kinds.get(norm, "").removeprefix("opt:") == "decimal":
            try:
                return Decimal(v)
            except InvalidOperation:
                raise Bad(f"{norm}: не десятичное число {v!r}") from None
        return v

    def norm_of(node, scope):
        base = scope[node.name][1] if node.name in scope else node.name
        return base + "".join("." + s.attr if s.attr is not None else "[]" for s in node.steps)

    def path(node, scope):
        head = node.name
        if head in scope:
            v, norm = scope[head]
        elif isinstance(values, dict) and head in values:
            v, norm = read(values[head], head), head
        else:
            raise Bad(f"нет значения {head}")
        for step in node.steps:
            if step.attr is not None:
                if not isinstance(v, dict):
                    raise Bad(f"{norm}: поле {step.attr} у значения {v!r}")
                v, norm = v.get(step.attr), f"{norm}.{step.attr}"
            else:
                i = value(step.idx, scope)
                if not isinstance(v, list) or type(i) is not int or not 0 <= i < len(v):
                    raise Bad(f"{norm}[{i}]: индекс вне списка")
                v, norm = v[i], norm + "[]"
            v = read(v, norm)
        return v

    def arith(node, scope):
        xs = [number(value(x, scope)) for x in node.args]
        if node.k == "neg":
            return -xs[0]
        (p, q), op = xs, node.op
        if op in ("/", "%") and q == 0:
            raise DivZero()
        if op == "+":
            return p + q
        if op == "-":
            return p - q
        if op == "*":
            return p * q
        return Decimal(p) / Decimal(q) if op == "/" else p % q

    def compare(node, scope):
        p, q = (value(x, scope) for x in node.args)
        op = node.op
        if op in ("==", "!="):
            return (p == q) == (op == "==")
        p, q = number(p), number(q)
        return p < q if op == "<" else p <= q if op == "<=" else p > q if op == ">" else p >= q

    def member(node, scope):
        v, c = (value(x, scope) for x in node.args)
        if isinstance(c, dict):
            return v in c
        if not isinstance(c, list):
            raise Bad(f"справа от in не набор и не список: {c!r}")
        return any(v == x for x in c)

    def func(node, scope):
        f, xs = node.name, [value(x, scope) for x in node.args]
        if f == "len":
            if not isinstance(xs[0], (str, list, dict)):
                raise Bad(f"len у значения {xs[0]!r}")
            return len(xs[0])
        if f == "startswith":
            if not all(isinstance(x, str) for x in xs):
                raise Bad("startswith не у строк")
            return xs[0].startswith(xs[1])
        xs = [number(x) for x in xs]
        if f == "abs":
            return abs(xs[0])
        return min(xs) if f == "min" else max(xs)

    def quant(node, scope):
        seq, norm = value(node.args[0], scope), norm_of(node.args[0], scope) + "[]"
        if not isinstance(seq, list):
            raise Bad(f"{node.op} не по списку: {seq!r}")
        body, var = node.args[1], node.name
        each = (value(body, {**scope, var: (read(x, norm), norm)}) for x in seq)
        if node.op == "forall":
            return all(truth(v) for v in each)
        if node.op == "exists":
            return any(truth(v) for v in each)
        if node.op == "count":
            return sum(1 for v in each if truth(v))
        return sum((number(v) for v in each), 0)

    def value(node, scope):
        k, a = node.k, node.args or []
        if k == "impl":
            return (not truth(value(a[0], scope))) or truth(value(a[1], scope))
        if k == "or":
            return truth(value(a[0], scope)) or truth(value(a[1], scope))
        if k == "and":
            return truth(value(a[0], scope)) and truth(value(a[1], scope))
        if k == "not":
            return not truth(value(a[0], scope))
        if k == "num":
            return Decimal(node.v) if isinstance(node.v, str) else node.v
        if k in ("str", "bool"):
            return node.v
        if k == "null":
            return None
        if k == "path":
            return path(node, scope)
        if k == "set":
            return [value(x, scope) for x in a]
        if k in ("neg", "arith"):
            return arith(node, scope)
        if k == "cmp":
            return compare(node, scope)
        if k == "in":
            return member(node, scope)
        return func(node, scope) if k == "func" else quant(node, scope)

    try:
        return EvalResult(ok=True, value=truth(value(typed.ast, {})))
    except DivZero:
        return EvalResult(ok=True, value=False)
    except (Bad, InvalidOperation, TypeError) as e:
        return EvalResult(ok=False, value=False, error=str(e) or repr(e))
