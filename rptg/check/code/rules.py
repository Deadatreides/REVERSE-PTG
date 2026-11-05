"""Лист rptg.check.code.rules — правила разбора кода функции для Э1 (LOGIC §5).

Функции приняты по карточке design/rptg.check.code.yaml; обвязку пишет скрипт. Перенос затравки
tools/leafcheck0.py: те же правила, но по коду из ответа модели и карточке из состояния.
"""
from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Answer, Json, Strings


def check(state: Json, answer: Answer) -> Strings:
    """Модуль — строка документации, импорты (и блок TYPE_CHECKING только с импортами) и один def
    операции; имена и порядок параметров, аннотации параметров и результата — как в карточке;
    импорты — allowed_imports узла, typing, __future__ и сгенерированные типы проекта
    (<корневой пакет>…_types); запрещены eval, exec, compile, __import__, globals, vars, доступ к
    __*__ и open без эффекта fs.*. Ответ не функция или не извлечён — пусто: провал извлечения
    покажет вердикт."""
    if answer.kind != "function" or not answer.ok:
        return []
    card = state["cards"][answer.node]
    op = next(o for o in card["ops"] if o["name"] == answer.op)
    try:
        tree = ast.parse(answer.code)
    except SyntaxError as e:
        return [f"строка {e.lineno}: код не разбирается — {e.msg}"]
    allowed = set(card["allowed_imports"]) | {"typing", "__future__"}
    forbidden = {"eval", "exec", "compile", "__import__", "globals", "vars", "open"}
    forbidden -= {"open"} if any(e.startswith("fs.") for e in card["effects"]) else set()
    imports = (ast.Import, ast.ImportFrom)

    def guarded(s):
        """Блок if TYPE_CHECKING: без else и только с импортами."""
        return isinstance(s, ast.If) and ast.unparse(s.test) == "TYPE_CHECKING" and not s.orelse             and all(isinstance(x, imports) for x in s.body)

    def layout():
        body = tree.body[1:] if ast.get_docstring(tree) is not None else tree.body
        defs = [s for s in body if isinstance(s, ast.FunctionDef) and s.name == op["name"]][:1]
        out = [f"строка {s.lineno}: на верхнем уровне только импорты и def {op['name']}"
               for s in body if not isinstance(s, imports) and not guarded(s) and s not in defs]
        return out + ([] if defs else [f"нет def {op['name']}"]), defs

    def imported(node):
        if isinstance(node, ast.ImportFrom):
            return [node.module or ""]
        return [a.name for a in node.names] if isinstance(node, ast.Import) else []

    def banned(m):
        generated = m.split(".")[0] == answer.node.split(".")[0] and m.endswith("._types")
        return m.split(".")[0] not in allowed and not generated

    def walk(node):
        out = [f"строка {node.lineno}: импорт {m} не из разрешённых {sorted(allowed - {'typing', '__future__'})}"
               for m in imported(node) if banned(m)]
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) in forbidden:
            out.append(f"строка {node.lineno}: запрещённый вызов {node.func.id}")
        if isinstance(node, ast.Attribute) and node.attr[:2] == node.attr[-2:] == "__":
            out.append(f"строка {node.lineno}: доступ к {node.attr}")
        return out

    def expected(t):
        simple = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}
        return f"list[{expected(t[1:-1])}]" if t[:1] + t[-1:] == "[]" else simple.get(t, t)

    def signature(fn):
        got, want = [a.arg for a in fn.args.args], [p["name"] for p in op["params"]]
        out = [] if got == want else [f"{fn.name}: параметры {got}, в карточке {want}"]
        pairs = [(f"аннотация {a.arg}", a.annotation, p["type"]) for a, p in zip(fn.args.args, op["params"])]
        pairs.append(("аннотация результата", fn.returns, op["result"]))
        return out + [f"{fn.name}: {what} — {ast.unparse(node) if node else None}, в карточке {expected(t)}"
                      for what, node, t in pairs if (ast.unparse(node) if node else None) != expected(t)]

    out, defs = layout()
    out += [p for node in ast.walk(tree) for p in walk(node)]
    return out + (signature(defs[0]) if defs else [])
