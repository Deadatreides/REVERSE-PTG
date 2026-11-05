"""Лист rptg.lang.cl.logic.schema — неявные факты из схем типов для формулы условия (LOGIC §4.3).

Функции приняты по карточке design/rptg.lang.cl.logic.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl.logic._types import SmtTerm

if TYPE_CHECKING:
    from rptg._types import Limits, TypeEnv


def facts(term: SmtTerm, env: TypeEnv, limits: Limits) -> SmtTerm:
    """Факты каждого символа формулы по его схеме: 0 ≤ длина ≤ K и minItems/maxItems у списка,
    длина словаря ≥ 0, minimum/maximum, minLength/maxLength, перечисление. У необязательного
    значения факт стоит под признаком |p?|: пока значения нет, ограничений нет. Символы — по
    порядку имён.
    """
    if not term.ok:
        return term
    types, names, sorts, found = env.types, env.vars, dict(term.sorts), list(term.facts)

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        return {"type": "array", "items": named(t[1:-1])} if t.startswith("[") else {"$ref": t}

    def resolve(s):
        seen = set()
        while "$ref" in s and s["$ref"] in types and s["$ref"] not in seen:
            seen.add(s["$ref"])
            s = types[s["$ref"]]
        return s

    def walk(sym):
        """нормальный путь символа и его схема: xs[1].a → xs[].a; корень — переменная окружения"""
        parts = sym.replace("[", ".[").split(".")
        norm, s = parts[0], named(names.get(parts[0], "Json"))
        for part in parts[1:]:
            s = resolve(s)
            if part.startswith("["):
                norm, s = norm + "[]", s.get("items", {})
            else:
                norm, s = f"{norm}.{part}", s.get("properties", {}).get(part, {})
        return norm, resolve(s)

    def literal(v, sort):
        text = str(v) + (".0" if sort == "Real" and isinstance(v, int) else "")
        return f"(- {text[1:]})" if text.startswith("-") else text

    def string(text):
        body = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else '""' if ch == '"'
                       else "\\u{%x}" % ord(ch) for ch in text)
        return f'"{body}"'

    def length(sym):
        norm, s = walk(sym[4:-1])
        dict_like = term.paths.get(norm, "").removeprefix("opt:") == "dict"
        out = [f"(<= 0 |{sym}|)" if dict_like else f"(<= 0 |{sym}| {limits.k_lists})"]
        return out + [f"({op} |{sym}| {s[key]})" for key, op in (("minItems", ">="), ("maxItems", "<=")) if key in s]

    def enum(sym, kind):
        if not kind.startswith("enum:"):
            return []
        eqs = [f"(= |{sym}| {string(v)})" for v in kind[5:].split(",")]
        return [eqs[0] if len(eqs) == 1 else f"(or {' '.join(eqs)})"]

    def value(sym):
        norm, s = walk(sym)
        kind, sort = term.paths.get(norm, ""), term.sorts[sym]
        out = enum(sym, kind.removeprefix("opt:"))
        bounds = [("minimum", "<=", True), ("exclusiveMinimum", "<", True), ("maximum", "<=", False),
                  ("exclusiveMaximum", "<", False)] if sort in ("Int", "Real") else []
        for key, op, low in bounds:
            if isinstance(s.get(key), (int, float)):
                n = literal(s[key], sort)
                out.append(f"({op} {n} |{sym}|)" if low else f"({op} |{sym}| {n})")
        for key, op in (("minLength", ">="), ("maxLength", "<=")) if sort == "String" else ():
            if isinstance(s.get(key), int):
                out.append(f"({op} (str.len |{sym}|) {s[key]})")
        if out and kind.startswith("opt:"):
            sorts[sym + "?"] = "Bool"
            out = [f"(=> |{sym}?| {c})" for c in out]
        return out

    for sym in sorted(term.sorts):
        if sym.endswith("?"):
            continue
        for f in length(sym) if sym.startswith("len(") else value(sym):
            if f not in found:
                found.append(f)
    return SmtTerm(ok=True, errors=[], term=term.term, sorts=sorts, facts=found, paths=term.paths)
