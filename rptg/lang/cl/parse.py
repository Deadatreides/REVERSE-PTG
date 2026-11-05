"""Лист rptg.lang.cl.parse — текст CL → дерево разбора по грамматике LOGIC §4.1.

Функции приняты по карточке design/rptg.lang.cl.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from rptg.lang.cl._types import ClAst, ClStep, ParseResult

if TYPE_CHECKING:
    from rptg._types import Cl


def parse(text: Cl) -> ParseResult:
    """Разбор с ошибками по позиции; имя поля после точки может быть служебным словом."""
    token = re.compile(r'(?P<num>\d+(?:\.\d+)?)|(?P<str>"(?:[^"\\]|\\.)*")'
                       r'|(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
                       r'|(?P<op>=>|==|!=|<=|>=|[<>+\-*/%()\[\]{},.:])')
    reserved = {"and", "or", "not", "in", "for", "forall", "exists", "true", "false", "null"}
    funcs = {"len", "abs", "min", "max", "startswith"}
    said = {"name": "имя", "num": "число", "str": "строка", "op": "знак"}
    toks, pos = [], 0
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        m = token.match(text, pos)
        if not m or m.lastgroup is None:
            return ParseResult(ok=False, errors=[f"позиция {pos}: непонятный знак {text[pos]!r}"])
        toks.append((m.lastgroup, m.group(), pos))
        pos = m.end()
    toks.append(("eof", "конец текста", len(text)))
    at = [0]

    class Bad(Exception):
        pass

    def peek(k=0):
        return toks[min(at[0] + k, len(toks) - 1)]

    def take():
        t = peek()
        at[0] += 1
        return t

    def is_(kind, val=None, k=0):
        t = peek(k)
        return t[0] == kind and (val is None or t[1] == val)

    def expect(kind, val=None):
        t = take()
        if t[0] != kind or (val is not None and t[1] != val):
            raise Bad(f"позиция {t[2]}: ожидалось {val or said[kind]}, стоит {t[1]!r}")
        return t

    def expr():
        a = or_()
        if is_("op", "=>"):
            take()
            return ClAst(k="impl", args=[a, expr()])
        return a

    def binary(kind, sub):
        a = sub()
        while is_("name", kind):
            take()
            a = ClAst(k=kind, args=[a, sub()])
        return a

    def or_():
        return binary("or", and_)

    def and_():
        return binary("and", not_)

    def not_():
        if is_("name", "not"):
            take()
            return ClAst(k="not", args=[not_()])
        return cmp()

    def cmp():
        a = arith()
        t = peek()
        if t[0] == "op" and t[1] in ("==", "!=", "<", "<=", ">", ">="):
            take()
            return ClAst(k="cmp", op=t[1], args=[a, arith()])
        if is_("name", "in"):
            take()
            return ClAst(k="in", args=[a, setlit() if is_("op", "{") else path()])
        return a

    def arith():
        a = term()
        while peek()[0] == "op" and peek()[1] in ("+", "-"):
            a = ClAst(k="arith", op=take()[1], args=[a, term()])
        return a

    def term():
        a = unary()
        while peek()[0] == "op" and peek()[1] in ("*", "/", "%"):
            a = ClAst(k="arith", op=take()[1], args=[a, unary()])
        return a

    def unary():
        if is_("op", "-"):
            take()
            if is_("num"):
                return number(take(), "-")
            return ClAst(k="neg", args=[unary()])
        return atom()

    def number(t, sign=""):
        s = sign + t[1]
        return ClAst(k="num", v=s if "." in s else int(s))

    def literal():
        t = take()
        if t[0] == "num":
            return number(t)
        if t[0] == "op" and t[1] == "-" and is_("num"):
            return number(take(), "-")
        if t[0] == "str":
            try:
                return ClAst(k="str", v=json.loads(t[1]))
            except ValueError:
                raise Bad(f"позиция {t[2]}: неверная строка {t[1]}") from None
        if t[0] == "name" and t[1] in ("true", "false"):
            return ClAst(k="bool", v=t[1] == "true")
        if t[0] == "name" and t[1] == "null":
            return ClAst(k="null")
        raise Bad(f"позиция {t[2]}: ожидался литерал, стоит {t[1]!r}")

    def setlit():
        expect("op", "{")
        items = [literal()]
        while is_("op", ","):
            take()
            items.append(literal())
        expect("op", "}")
        return ClAst(k="set", args=items)

    def name():
        t = expect("name")
        if t[1] in reserved:
            raise Bad(f"позиция {t[2]}: служебное слово {t[1]!r} вместо имени")
        return t[1]

    def binder():
        var = name()
        expect("name", "in")
        return var, path()

    def atom():
        t = peek()
        if t[0] in ("num", "str") or (t[0] == "name" and t[1] in ("true", "false", "null")):
            return literal()
        if is_("op", "("):
            take()
            e = expr()
            expect("op", ")")
            return e
        if t[0] == "name" and t[1] in ("forall", "exists"):
            take()
            var, p = binder()
            expect("op", ":")
            return ClAst(k="quant", op=t[1], name=var, args=[p, expr()])
        if t[0] == "name" and t[1] in ("sum", "count") and is_("op", "(", 1):
            take()
            take()
            e = expr()
            expect("name", "for")
            var, p = binder()
            expect("op", ")")
            return ClAst(k="agg", op=t[1], name=var, args=[p, e])
        if t[0] == "name" and t[1] in funcs and is_("op", "(", 1):
            take()
            take()
            args = [expr()]
            while is_("op", ","):
                take()
                args.append(expr())
            expect("op", ")")
            return ClAst(k="func", name=t[1], args=args)
        if t[0] == "name":
            return path()
        raise Bad(f"позиция {t[2]}: неожиданное {t[1]!r}")

    def path():
        head = name()
        steps: list[ClStep] = []
        while True:
            if is_("op", "."):
                take()
                steps.append(ClStep(attr=expect("name")[1]))
            elif is_("op", "["):
                take()
                steps.append(ClStep(idx=arith()))
                expect("op", "]")
            else:
                return ClAst(k="path", name=head, steps=steps)

    try:
        ast = expr()
        if peek()[0] != "eof":
            t = peek()
            raise Bad(f"позиция {t[2]}: лишнее в конце: {t[1]!r}")
    except Bad as e:
        return ParseResult(ok=False, errors=[str(e)])
    return ParseResult(ok=True, errors=[], ast=ast)
