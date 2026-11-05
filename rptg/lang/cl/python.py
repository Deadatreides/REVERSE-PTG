"""Лист rptg.lang.cl.python — дерево → выражение Python для обёрток условий и тестов.

Функции приняты по карточке design/rptg.lang.cl.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg.lang.cl._types import Typed


def python(typed: Typed) -> str:
    """Каждая бинарная операция в скобках; квантор — all/any; десятичный литерал — Decimal('…').

    Значения — объекты dataclasses: поле записи — атрибут, у необязательного поля без значения —
    None. Поле или переменная, чьё имя — слово Python, получает подчёркивание (example.in →
    example.in_), как в сгенерированных типах. Путь вида decimal оборачивается в Decimal(…):
    "12.50" хранится строкой. Условие без типов даёт False — обёртка сообщит нарушение, а не
    пропустит его.
    """
    if not typed.ok or typed.ast is None:
        return "False"
    kinds = typed.paths
    words = {"False", "None", "True", "and", "as", "assert", "async", "await", "break", "class",
             "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global",
             "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
             "try", "while", "with", "yield"}

    def ident(name):
        return name + "_" if name in words else name

    def norm_of(node, scope):
        base = scope.get(node.name, node.name)
        return base + "".join("." + s.attr if s.attr is not None else "[]" for s in node.steps)

    def path(node, scope, raw=False):
        norm, out = scope.get(node.name, node.name), ident(node.name)
        for s in node.steps:
            if s.attr is not None:
                norm, out = f"{norm}.{s.attr}", f"{out}.{ident(s.attr)}"
            else:
                norm, out = norm + "[]", out + f"[{py(s.idx, scope)}]"
        if not raw and kinds.get(norm, "").removeprefix("opt:") == "decimal":
            return f"Decimal({out})"
        return out

    def quant(node, scope):
        lst, body = node.args
        var, src = ident(node.name), path(lst, scope, raw=True)
        b = py(body, {**scope, node.name: norm_of(lst, scope) + "[]"})
        if node.op in ("forall", "exists"):
            return f"{'all' if node.op == 'forall' else 'any'}({b} for {var} in {src})"
        if node.op == "count":
            return f"sum(1 for {var} in {src} if {b})"
        return f"sum({b} for {var} in {src})"

    def null_cmp(node, scope):
        a = node.args
        x = a[1] if a[0].k == "null" else a[0]
        side = path(x, scope, raw=True) if x.k == "path" else py(x, scope)
        return f"({side} is {'not ' if node.op == '!=' else ''}None)"

    def py(node, scope):
        k, a = node.k, node.args or []
        if k == "impl":
            return f"((not {py(a[0], scope)}) or {py(a[1], scope)})"
        if k in ("and", "or"):
            return f"({py(a[0], scope)} {k} {py(a[1], scope)})"
        if k == "not":
            return f"(not {py(a[0], scope)})"
        if k == "cmp" and "null" in (a[0].k, a[1].k):
            return null_cmp(node, scope)
        if k in ("cmp", "arith"):
            return f"({py(a[0], scope)} {node.op} {py(a[1], scope)})"
        if k == "neg":
            return f"(-{py(a[0], scope)})"
        if k == "in":
            rhs = a[1]
            items = "(" + ", ".join(py(x, scope) for x in rhs.args) + ",)" if rhs.k == "set" else None
            return f"({py(a[0], scope)} in {items or py(rhs, scope)})"
        if k == "num":
            return f"Decimal('{node.v}')" if isinstance(node.v, str) else str(node.v)
        if k == "str":
            return json.dumps(node.v, ensure_ascii=False)
        if k in ("bool", "null"):
            return {True: "True", False: "False", None: "None"}[node.v]
        if k == "path":
            return path(node, scope)
        if k == "func" and node.name == "startswith":
            return f"{py(a[0], scope)}.startswith({py(a[1], scope)})"
        if k == "func":
            return f"{node.name}({', '.join(py(x, scope) for x in a)})"
        return quant(node, scope)

    return py(typed.ast, {})
