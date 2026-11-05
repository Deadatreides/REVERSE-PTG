"""Лист rptg.lang.cl.logic.smt — типизированное условие → формула SMT-LIB (LOGIC §4.4).

Функции приняты по карточке design/rptg.lang.cl.logic.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl.logic._types import SmtTerm

if TYPE_CHECKING:
    from rptg._types import Limits
    from rptg.lang.cl._types import Typed


def term(typed: Typed, limits: Limits) -> SmtTerm:
    """Формула условия и сорта её символов; неявные факты типов добавляет лист schema.

    Символ — путь CL в кавычках: |x|, |order.total|, |xs[1]|; длина списка — |len(xs)|, признак
    «не null» — |p?|. Список ограничен длиной K = limits.k_lists: forall — конъюнкция по i < K с
    посылкой |len(xs)| > i. Деление на ноль и индекс вне списка делают условие ложным, как при
    вычислении (LOGIC §4.3): у каждого подвыражения есть формула «определено», связки учитывают
    короткое вычисление слева направо. Целое в вещественном месте — (to_real …), литерал — 1.0.
    """
    if not typed.ok or typed.ast is None:
        return SmtTerm(ok=False, errors=list(typed.errors) or ["условие не типизировано"], term="", sorts={},
                       facts=[], paths={})
    kinds, K = typed.paths, limits.k_lists
    sorts: dict = {}
    TRUE = "true"

    class Bad(Exception):
        pass

    def nary(op, xs, unit):
        xs = [x for x in xs if x != TRUE] if op == "and" else list(xs)
        return unit if not xs else xs[0] if len(xs) == 1 else f"({op} {' '.join(xs)})"

    def conj(*xs):
        return nary("and", xs, TRUE)

    def implies(a, b):
        return TRUE if b == TRUE else b if a == TRUE else f"(=> {a} {b})"

    def numeral(v, sort="Int"):
        s = str(v) + (".0" if sort == "Real" and "." not in str(v) else "")
        return f"(- {s[1:]})" if s.startswith("-") else s

    def lit(text):
        body = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else '""' if ch == '"'
                       else "\\u{%x}" % ord(ch) for ch in text)
        return f'"{body}"'

    def real(t, sort):
        if sort == "Real":
            return t
        return t + ".0" if t.isdigit() else f"(- {t[3:-1]}.0)" if t.startswith("(- ") and t[3:-1].isdigit() \
            else f"(to_real {t})"

    def coerce(x, sx, y, sy):
        if {sx, sy} == {"Int", "Real"}:
            return real(x, sx), real(y, sy), "Real"
        return x, y, sx

    def sort_of(kind, where):
        k = kind.removeprefix("opt:")
        if k in ("integer", "number", "decimal", "boolean", "string") or k.startswith("enum:"):
            return {"integer": "Int", "number": "Real", "decimal": "Real", "boolean": "Bool"}.get(k, "String")
        raise Bad(f"{where}: вид {kind or '?'} не кодируется в символ")

    def length(c, norm):
        sorts.setdefault(f"len({c})", "Int")
        return f"|len({c})|"

    def alts(node, scope):
        """варианты пути [(условие, конкретный путь)], нормальный путь, «определено»"""
        base, norm = scope.get(node.name, (node.name, node.name))
        out, d = [(TRUE, base)], TRUE
        for step in node.steps:
            if step.attr is not None:
                out, norm = [(g, f"{c}.{step.attr}") for g, c in out], f"{norm}.{step.attr}"
                continue
            i, _, di = enc(step.idx, scope)
            d, new = conj(d, di), []
            for g, c in out:
                d = conj(d, implies(g, f"(and (<= 0 {i}) (< {i} {length(c, norm)}))"))
                picks = [int(i)] if i.isdigit() else range(K)
                new += [(conj(g, TRUE if i.isdigit() else f"(= {i} {j})"), f"{c}[{j}]") for j in picks]
            out, norm = new, norm + "[]"
        return out, norm, d

    def pick(out, fmt):
        t = fmt.format(out[-1][1])
        for g, c in reversed(out[:-1]):
            t = f"(ite {g} {fmt.format(c)} {t})"
        return t

    def value(node, scope):
        out, norm, d = alts(node, scope)
        sort = sort_of(kinds.get(norm, ""), norm)
        for _, c in out:
            sorts.setdefault(c, sort)
        return pick(out, "|{}|"), sort, d

    def presence(node, scope):
        out, norm, d = alts(node, scope)
        for _, c in out:
            sorts.setdefault(c + "?", "Bool")
        return pick(out, "|{}?|"), d

    def single_list(node, scope, what):
        out, norm, d = alts(node, scope)
        if len(out) != 1:
            raise Bad(f"{norm}: {what} по списку с переменным индексом не кодируется")
        return out[0][1], norm, d

    def logic(node, scope):
        a, k = node.args, node.k
        x, _, dx = enc(a[0], scope)
        if k == "not":
            return f"(not {x})", "Bool", dx
        y, _, dy = enc(a[1], scope)
        guard, sym = (f"(not {x})" if k == "or" else x), {"and": "and", "or": "or", "impl": "=>"}[k]
        return f"({sym} {x} {y})", "Bool", conj(dx, implies(guard, dy))

    def arith(node, scope):
        parts = [enc(x, scope) for x in node.args]
        d = conj(*(p[2] for p in parts))
        if node.k == "neg":
            return f"(- {parts[0][0]})", parts[0][1], d
        (x, sx, _), (y, sy, _) = parts
        op = node.op
        if op in ("/", "%"):
            d = conj(d, f"(not (= {y} {numeral(0, sy)}))")
        if op == "/":
            return f"(/ {real(x, sx)} {real(y, sy)})", "Real", d
        if op == "%":
            m = f"(mod {x} {y})"
            return f"(ite (< {y} 0) (ite (= {m} 0) 0 (+ {m} {y})) {m})", "Int", d
        x, y, sort = coerce(x, sx, y, sy)
        return f"({op} {x} {y})", sort, d

    def compare(node, scope):
        a, op = node.args, node.op
        if "null" in (a[0].k, a[1].k):
            x = a[1] if a[0].k == "null" else a[0]
            if x.k == "null":
                return ("true" if op == "==" else "false"), "Bool", TRUE
            p, d = presence(x, scope)
            return (f"(not {p})" if op == "==" else p), "Bool", d
        (x, sx, dx), (y, sy, dy) = enc(a[0], scope), enc(a[1], scope)
        x, y, _ = coerce(x, sx, y, sy)
        text = f"(= {x} {y})" if op in ("==", "!=") else f"({op} {x} {y})"
        return (f"(not {text})" if op == "!=" else text), "Bool", conj(dx, dy)

    def member(node, scope):
        (x, sx, dx), rhs = enc(node.args[0], scope), node.args[1]
        if rhs.k == "set":
            opts = []
            for item in rhs.args:
                t, s, _ = enc(item, scope)
                a, b, _ = coerce(x, sx, t, s)
                opts.append(f"(= {a} {b})")
            return nary("or", opts, "false"), "Bool", dx
        c, norm, d = single_list(rhs, scope, "in")
        if kinds.get(norm, "").removeprefix("opt:") != "list":
            raise Bad(f"{norm}: «ключ in словарь» не кодируется")
        sort, n, opts = sort_of(kinds.get(norm + "[]", ""), norm + "[]"), length(c, norm), []
        for i in range(K):
            sorts.setdefault(f"{c}[{i}]", sort)
            a, b, _ = coerce(x, sx, f"|{c}[{i}]|", sort)
            opts.append(f"(and (> {n} {i}) (= {a} {b}))")
        return nary("or", opts, "false"), "Bool", conj(dx, d)

    def func(node, scope):
        f, a = node.name, node.args
        if f == "len" and a[0].k == "path":
            out, norm, d = alts(a[0], scope)
            if kinds.get(norm, "").removeprefix("opt:") in ("list", "dict"):
                return pick([(g, length(c, norm)) for g, c in out], "{}"), "Int", d
        parts = [enc(x, scope) for x in a]
        d = conj(*(p[2] for p in parts))
        if f == "len":
            return f"(str.len {parts[0][0]})", "Int", d
        if f == "startswith":
            return f"(str.prefixof {parts[1][0]} {parts[0][0]})", "Bool", d
        sort = "Real" if any(p[1] == "Real" for p in parts) else "Int"
        xs = [real(p[0], p[1]) if sort == "Real" else p[0] for p in parts]
        if f == "abs":
            return f"(ite (>= {xs[0]} {numeral(0, sort)}) {xs[0]} (- {xs[0]}))", sort, d
        acc, cmp = xs[0], "<=" if f == "min" else ">="
        for x in xs[1:]:
            acc = f"(ite ({cmp} {acc} {x}) {acc} {x})"
        return acc, sort, d

    def quant(node, scope):
        c, norm, d = single_list(node.args[0], scope, node.op)
        n, op, items = length(c, norm), node.op, []
        for i in range(K):
            t, s, di = enc(node.args[1], {**scope, node.name: (f"{c}[{i}]", norm + "[]")})
            items.append((f"(> {n} {i})", t, s, di))
        if op in ("forall", "exists"):
            vals = [f"(=> {g} {t})" if op == "forall" else f"(and {g} {t})" for g, t, _, _ in items]
            defs, reached = [], []
            for g, t, _, di in items:
                defs.append(implies(conj(g, *reached), di))
                reached.append(t if op == "forall" else f"(not {t})")
            return nary("and" if op == "forall" else "or", vals, TRUE), "Bool", conj(d, *defs)
        sort = "Real" if op == "sum" and any(s == "Real" for _, _, s, _ in items) else "Int"
        zero = numeral(0, sort)
        if op == "sum":
            terms = [f"(ite {g} {real(t, s) if sort == 'Real' else t} {zero})" for g, t, s, _ in items]
        else:
            terms = [f"(ite (and {g} {t}) 1 0)" for g, t, _, _ in items]
        return nary("+", terms, zero), sort, conj(d, *(implies(g, di) for g, _, _, di in items))

    def enc(node, scope):
        k, v = node.k, node.v
        if k in ("num", "str", "bool"):
            sort = {"num": "Real" if isinstance(v, str) else "Int", "str": "String", "bool": "Bool"}[k]
            return (numeral(v) if k == "num" else lit(v) if k == "str" else "true" if v else "false"), sort, TRUE
        rule = {"and": logic, "or": logic, "impl": logic, "not": logic, "path": value, "arith": arith,
                "neg": arith, "cmp": compare, "in": member, "func": func, "quant": quant, "agg": quant}.get(k)
        if rule is None:
            raise Bad(f"узел {k} вне своего места")
        return rule(node, scope)

    try:
        t, _, d = enc(typed.ast, {})
    except Bad as e:
        return SmtTerm(ok=False, errors=[str(e)], term="", sorts=sorts, facts=[], paths=kinds)
    return SmtTerm(ok=True, errors=[], term=conj(d, t), sorts=sorts, facts=[], paths=kinds)
