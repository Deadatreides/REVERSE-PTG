"""Лист rptg.lang.cl.typecheck — типы узлов дерева по окружению (LOGIC §4.2).

Функции приняты по карточке design/rptg.lang.cl.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.lang.cl._types import Typed

if TYPE_CHECKING:
    from rptg._types import TypeEnv
    from rptg.lang.cl._types import ParseResult


def typecheck(parsed: ParseResult, env: TypeEnv) -> Typed:
    """Проверить типы; необязательное значение — только под != null в той же конъюнкции или посылке.

    paths — вид каждого пути и его начал (integer, number, decimal, string, boolean, enum:A,B, list,
    record, dict, json; opt: — у необязательного поля), переменная квантора и индекс — []. Первое
    нарушение останавливает проверку и называет место.
    """
    if not parsed.ok or parsed.ast is None:
        return Typed(ok=False, errors=list(parsed.errors) or ["условие не разобрано"], type="", paths={})
    types, names, paths, num = env.types, env.vars, {}, ("integer", "number", "decimal")

    class Bad(Exception):
        pass

    def show(n):
        k, a = n.k, n.args or []
        if k == "path":
            return n.name + "".join("." + s.attr if s.attr is not None else f"[{show(s.idx)}]" for s in n.steps)
        if k in ("num", "str", "bool", "null"):
            return {"num": str(n.v), "str": f'"{n.v}"', "bool": str(n.v).lower(), "null": "null"}[k]
        if k in ("cmp", "arith", "and", "or", "in", "impl"):
            return f"{show(a[0])} {n.op or {'impl': '=>'}.get(k, k)} {show(a[1])}"
        if k in ("not", "neg"):
            return ("not " if k == "not" else "-") + show(a[0])
        if k in ("set", "func"):
            inner = ", ".join(show(x) for x in a)
            return "{" + inner + "}" if k == "set" else f"{n.name}({inner})"
        if k == "quant":
            return f"{n.op} {n.name} in {show(a[0])}: {show(a[1])}"
        return f"{n.op}({show(a[1])} for {n.name} in {show(a[0])})"

    def need(ok, node, what):
        if not ok:
            raise Bad(f"«{show(node)}»: {what}")

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        if t.startswith("[") and t.endswith("]"):
            return {"type": "array", "items": named(t[1:-1])}
        return {"$ref": t}

    def resolve(s):
        seen = set()
        while "$ref" in s and s["$ref"] != "Decimal":
            ref = s["$ref"]
            if ref in seen or ref not in types:
                raise Bad(f"тип {ref} не найден в окружении")
            seen.add(ref)
            s = types[ref]
        return s

    def kind(schema):
        s = resolve(schema)
        enum, t = s.get("enum"), s.get("type")
        if s.get("$ref") == "Decimal":
            return "decimal"
        if isinstance(enum, list) and enum and all(isinstance(v, str) for v in enum):
            return "enum:" + ",".join(enum)
        if t == "object":
            return "record" if "properties" in s else "dict"
        return {"integer": "integer", "number": "number", "string": "string", "boolean": "boolean",
                "array": "list"}.get(t, "json")

    def textual(k):
        return k == "string" or k.startswith("enum:")

    def unsure(*ks):
        return any(k.startswith("opt:") for k in ks)

    def same(a, b):
        return (a in num and b in num) or (textual(a) and textual(b)) or a == b == "boolean"

    def in_enum(k, node, lit):
        if k.startswith("enum:") and lit.k == "str":
            need(lit.v in k[5:].split(","), node, f"{lit.v!r} не из перечисления {k[5:]}")

    def path(node, scope, guards):
        head = node.name
        if head in scope:
            norm, schema = scope[head]
        elif head in names:
            norm, schema = head, named(names[head])
        else:
            raise Bad(f"«{head}»: имя не объявлено")
        k, opt = kind(schema), False
        paths.setdefault(norm, k)
        for step in node.steps:
            need(not opt or norm in guards, node, f"{norm} может быть null — нужна проверка {norm} != null")
            s = resolve(schema)
            if step.attr is not None:
                f = step.attr
                need(k == "record", node, f"поле {f} не у записи: {norm} — {k}")
                need(f in s["properties"], node, f"у {norm} нет поля {f}")
                schema, opt, norm = s["properties"][f], f not in s.get("required", []), f"{norm}.{f}"
            else:
                need(k == "list", node, f"индекс не у списка: {norm} — {k}")
                need(expr(step.idx, scope, guards) == "integer", node, "индекс не целый")
                schema, opt, norm = s.get("items", {}), False, norm + "[]"
            k = kind(schema)
            paths[norm] = ("opt:" if opt else "") + k
        return ("opt:" + k if opt and norm not in guards else k), schema, norm

    def norm_of(node, scope):
        base = scope[node.name][0] if node.name in scope else node.name
        return base + "".join("." + s.attr if s.attr is not None else "[]" for s in node.steps)

    def facts(node, scope, when):
        """пути, которые не null, когда условие равно when"""
        k, a = node.k, node.args or []
        if k == "cmp" and node.op in ("==", "!=") and (node.op == "!=") == when:
            for x, y in ((a[0], a[1]), (a[1], a[0])):
                if x.k == "path" and y.k == "null":
                    return {norm_of(x, scope)}
        if k == ("and" if when else "or"):
            return facts(a[0], scope, when) | facts(a[1], scope, when)
        if k == "not":
            return facts(a[0], scope, not when)
        return set()

    def logic(node, scope, guards):
        a = node.args
        left = expr(a[0], scope, guards)
        need(left == "boolean", node, f"операнд не логический: {left}")
        if node.k != "not":
            right = expr(a[1], scope, guards | facts(a[0], scope, node.k != "or"))
            need(right == "boolean", node, f"операнд не логический: {right}")
        return "boolean"

    def arith(node, scope, guards):
        ks = [expr(x, scope, guards) for x in node.args]
        need(all(x in num for x in ks), node, "арифметика не над числами: " + ", ".join(ks))
        need(not ("decimal" in ks and "number" in ks), node, "смешаны decimal и number")
        need(node.op != "%" or ks == ["integer", "integer"], node, "% — только у целых")
        if "decimal" in ks:
            return "decimal"
        return "number" if node.op == "/" or "number" in ks else "integer"

    def compare(node, scope, guards):
        a, op = node.args, node.op
        left, right = expr(a[0], scope, guards), expr(a[1], scope, guards)
        if "null" in (left, right):
            other = right if left == "null" else left
            need(op in ("==", "!="), node, "с null сравнивают только == и !=")
            need(other.startswith("opt:") or other in ("json", "null"), node, f"{other} не бывает null")
            return "boolean"
        need(not unsure(left, right), node, "значение может быть null — нужна проверка != null")
        if op in ("<", "<=", ">", ">="):
            need(left in num and right in num, node, f"порядок — только у чисел: {left}, {right}")
        else:
            need(same(left, right), node, f"сравниваются разные виды: {left}, {right}")
            in_enum(left, node, a[1])
            in_enum(right, node, a[0])
        return "boolean"

    def member(node, scope, guards):
        a = node.args
        left = expr(a[0], scope, guards)
        need(not unsure(left), node, "значение может быть null — нужна проверка != null")
        if a[1].k == "set":
            for x in a[1].args:
                right = expr(x, scope, guards)
                need(same(left, right), node, f"в наборе {right}, а слева {left}")
                in_enum(left, node, x)
            return "boolean"
        right, schema, _ = path(a[1], scope, guards)
        if right == "dict":
            need(textual(left), node, "ключ словаря — строка")
        else:
            need(right == "list", node, f"справа от in — набор, список или словарь, а не {right}")
            need(same(left, kind(resolve(schema).get("items", {}))), node, "элемент списка другого вида")
        return "boolean"

    def func(node, scope, guards):
        f, ks = node.name, [expr(x, scope, guards) for x in node.args]
        need(not unsure(*ks), node, "значение может быть null — нужна проверка != null")
        if f == "len":
            need(len(ks) == 1 and (textual(ks[0]) or ks[0] in ("list", "dict")), node,
                 "len — у строки, списка или словаря")
            return "integer"
        if f == "startswith":
            need(len(ks) == 2 and all(textual(x) for x in ks), node, "startswith — у двух строк")
            return "boolean"
        need(all(x in num for x in ks) and (f != "abs" or len(ks) == 1), node, f"{f} — у чисел")
        need(not ("decimal" in ks and "number" in ks), node, "смешаны decimal и number")
        return "decimal" if "decimal" in ks else "number" if "number" in ks else "integer"

    def quant(node, scope, guards):
        lk, schema, norm = path(node.args[0], scope, guards)
        need(lk == "list", node, f"{node.op} идёт по списку, а {norm} — {lk}")
        items = resolve(schema).get("items", {})
        paths[norm + "[]"] = kind(items)
        body = expr(node.args[1], {**scope, node.name: (norm + "[]", items)}, guards)
        if node.op == "sum":
            need(body in num, node, f"sum — по числам, а тело — {body}")
            return body
        need(body == "boolean", node, f"тело {node.op} не логическое: {body}")
        return "integer" if node.op == "count" else "boolean"

    def expr(node, scope, guards):
        k = node.k
        if k == "num":
            return "integer" if isinstance(node.v, int) else "decimal"
        if k in ("str", "bool", "null"):
            return {"str": "string", "bool": "boolean", "null": "null"}[k]
        if k == "path":
            return path(node, scope, guards)[0]
        rule = {"impl": logic, "and": logic, "or": logic, "not": logic, "neg": arith, "arith": arith,
                "cmp": compare, "in": member, "func": func, "quant": quant, "agg": quant}.get(k)
        if rule is None:
            raise Bad(f"«{show(node)}»: {k} не на своём месте")
        return rule(node, scope, guards)

    ast = parsed.ast
    try:
        top = expr(ast, {}, frozenset())
        need(top == "boolean", ast, f"условие не логическое: {top}")
    except Bad as e:
        return Typed(ok=False, errors=[str(e)], type="", ast=ast, paths=paths)
    return Typed(ok=True, errors=[], type="boolean", ast=ast, paths=paths)
