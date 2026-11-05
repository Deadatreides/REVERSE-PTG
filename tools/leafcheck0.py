"""Затравка Э1 (LOGIC §5): статика функций финальных узлов, у которых есть код.

Правила:
  * модуль листа — строка документации, импорты и ровно по одному def на операцию карточки;
  * имена и порядок параметров — как в карточке, у каждого параметра и результата есть аннотация;
  * импорты — из allowed_imports узла, плюс typing, __future__ и сгенерированные типы проекта
    (<корневой пакет>…_types); в блоке TYPE_CHECKING — только импорты;
  * запрещённые встроенные: eval, exec, compile, __import__, globals, vars, доступ к __*__,
    open без эффекта fs.*;
  * размер — функция, а не константа (REVERSE-PTG-LIMIT-FUNCTION.md):
      - строк кода не больше 2·D_код + S + 10, где D_код — решения в самом коде, S — прямолинейные
        шаги, которых требует договор (project.yaml, contracts; у разборщика грамматики — символы
        правых частей, у остальных 0), строки кода — без документации, комментариев и пустых. На 21
        функции листьев lang строк кода ≈ 2 на решение (наклон 2,00, R² 0,90), запас 10 = свободный
        член −4,6 + 2σ;
      - если договорное число решений D объявлено (contracts), решений в коде не больше 1,5·D + 5:
        больше — договор занижен или код раздут;
      - явный ручной предел физических строк (overrides: max_lines) действует сверх этого;
  * цикломатическая сложность каждого блока (функции и каждой вложенной функции отдельно, как
    считает radon) не больше предела; ручные назначения узла (overrides) его ослабляют.

Сложность и число решений даёт radon (cc_visit), вложенные функции — отдельными блоками. Без
radon — своя таблица по его документации: блок начинается с 1; +1 дают if, elif, for, while,
каждый except, with, assert, генератор и каждый оператор and/or; else и finally — 0; сверх
таблицы, как в коде radon, +1 за условное выражение и за каждый if внутри генератора. 28.09.2026
обе дали одно и то же на всех 135 блоках листьев lang; tests/test_leafcheck_controls.py держит
это совпадение.

    python tools/leafcheck0.py
"""
import ast
import sys
from pathlib import Path

import yaml

try:
    from radon.complexity import cc_visit
except ImportError:  # без radon — своя таблица, совпадающая с ним
    cc_visit = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

DESIGN = ROOT / "design"
FORBIDDEN = {"eval", "exec", "compile", "__import__", "globals", "vars"}
PRIMITIVE_PY = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}
LINES_PER_DECISION = 2   # строка проверки и строка действия; наклон подгонки на 21 функции — 2,0005
LINES_MARGIN = 10        # свободный член подгонки −4,6 плюс 2σ остатков (σ ≈ 7 на 19 функциях без выбросов)
DECISIONS_SLACK = (1.5, 5)  # решений в коде ≤ 1,5·D + 5: запас на неточность договорной разметки (±25 %)


def line_limit(decisions, sequence=0):
    """Предел строк кода: L = 2·D + S + 10."""
    return LINES_PER_DECISION * decisions + sequence + LINES_MARGIN


def complexity(fn):
    """Сложность блока без вложенных функций; вложенные — отдельными блоками."""
    blocks = []

    def visit(node, top):
        score = 0
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not top:
                blocks.append((child.name, 1 + visit(child, child)))
                continue
            if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.Assert,
                                  ast.ExceptHandler, ast.With, ast.AsyncWith)):
                score += 1
            elif isinstance(child, ast.BoolOp):
                score += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                score += 1 + len(child.ifs)
            score += visit(child, top)
        return score

    blocks.insert(0, (fn.name, 1 + visit(fn, fn)))
    return blocks


def radon_blocks(source_text):
    """Блоки radon по функциям верхнего уровня: {имя: [(блок, сложность), …]}; без radon — пусто."""
    if cc_visit is None:
        return {}
    out = {}

    def walk(f, acc):
        acc.append((f.name, f.complexity))
        for c in f.closures:
            walk(c, acc)

    for f in cc_visit(source_text):
        acc = []
        walk(f, acc)
        out[f.name] = acc
    return out


def code_lines(fn, source):
    """Строки кода функции: физические без пустых, комментариев и строк документации (своей и вложенных)."""
    doc = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                doc.update(range(first.lineno, first.end_lineno + 1))
    lines = source[fn.lineno - 1:fn.end_lineno]
    return sum(1 for number, text in enumerate(lines, start=fn.lineno)
               if text.strip() and not text.strip().startswith("#") and number not in doc)


def ann_text(node):
    return ast.unparse(node) if node is not None else None


def expected_ann(t):
    if t in PRIMITIVE_PY:
        return PRIMITIVE_PY[t]
    if t.startswith("[") and t.endswith("]"):
        return f"list[{expected_ann(t[1:-1])}]"
    return t


def check_leaf(card, path, limits, override, contracts=None):
    """Замечания Э1 по модулю листа, размеры функций и пределы.

    contracts — договоры операций узла: {имя операции: {decisions: D, sequence: S}}.
    """
    problems = []
    source_text = path.read_text(encoding="utf-8")
    source = source_text.splitlines()
    tree = ast.parse(source_text)
    allowed = set(card.get("allowed_imports", [])) | {"typing", "__future__"}
    ops = {o["name"]: o for o in card["ops"]}
    contracts = contracts or {}
    defs = {}
    for i, stmt in enumerate(tree.body):
        if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(stmt, ast.If) and ast.unparse(stmt.test) == "TYPE_CHECKING" and not stmt.orelse and all(
                isinstance(s, (ast.Import, ast.ImportFrom)) for s in stmt.body):
            continue
        if isinstance(stmt, ast.FunctionDef) and stmt.name in ops and stmt.name not in defs:
            defs[stmt.name] = stmt
            continue
        problems.append(f"строка {stmt.lineno}: на верхнем уровне листа только импорты и def операций")
    for name in ops:
        if name not in defs:
            problems.append(f"нет def {name}")
    package = card["id"].split(".")[0]  # сгенерированные типы проекта лежат в его корневом пакете
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [node.module or ""]
        for mod in mods:
            generated = mod.split(".")[0] == package and mod.split(".")[-1] == "_types"
            if mod.split(".")[0] not in allowed and not generated:
                problems.append(f"строка {node.lineno}: импорт {mod} не из разрешённых {sorted(allowed - {'typing', '__future__'})}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN or (node.func.id == "open" and not any(
                    e.startswith("fs.") for e in card.get("effects", []))):
                problems.append(f"строка {node.lineno}: запрещённый вызов {node.func.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr.endswith("__"):
            problems.append(f"строка {node.lineno}: доступ к {node.attr}")
    max_lines = override.get("max_lines", limits["final_max_lines"])
    max_cc = override.get("max_complexity", limits["max_complexity"])
    measured = radon_blocks(source_text)
    stats = []
    for name, fn in defs.items():
        op = ops[name]
        got = [a.arg for a in fn.args.args]
        want = [p["name"] for p in op["params"]]
        if got != want:
            problems.append(f"{name}: параметры {got}, в карточке {want}")
        for a, p in zip(fn.args.args, op["params"]):
            if ann_text(a.annotation) != expected_ann(p["type"]):
                problems.append(f"{name}: аннотация {a.arg} — {ann_text(a.annotation)}, в карточке {expected_ann(p['type'])}")
        if ann_text(fn.returns) != expected_ann(op["result"]):
            problems.append(f"{name}: аннотация результата — {ann_text(fn.returns)}, в карточке {expected_ann(op['result'])}")
        blocks = measured.get(name) or complexity(fn)
        realized = sum(cc - 1 for _, cc in blocks)
        contract = contracts.get(name) or {}
        sequence, declared = contract.get("sequence", 0), contract.get("decisions")
        code, limit = code_lines(fn, source), line_limit(realized, sequence)
        if code > limit:
            problems.append(f"{name}: строк кода {code}, предел 2·{realized} + {sequence} + 10 = {limit}")
        if declared is not None and realized > DECISIONS_SLACK[0] * declared + DECISIONS_SLACK[1]:
            problems.append(f"{name}: решений в коде {realized}, по договору {declared} — больше 1,5·D + 5 = "
                            f"{DECISIONS_SLACK[0] * declared + DECISIONS_SLACK[1]:g}: договор занижен или код раздут")
        lines = fn.end_lineno - fn.lineno + 1
        if "max_lines" in override and lines > max_lines:
            problems.append(f"{name}: строк {lines}, ручной предел {max_lines}")
        size = f"строк кода {code}/{limit}, решений {realized}" + (f" из договорных {declared}" if declared is not None else "")
        for block, cc in blocks:
            if cc > max_cc:
                problems.append(f"{name}: сложность блока {block} — {cc}, предел {max_cc}")
        stats.append((name, size, max(cc for _, cc in blocks)))
    return problems, stats, (max_lines, max_cc)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    project = yaml.safe_load((DESIGN / "project.yaml").read_text(encoding="utf-8"))
    limits, overrides = project["limits"], project.get("overrides") or {}
    contracts = project.get("contracts") or {}
    designs = [d for _, d in design_io.designs(DESIGN)]
    composite = {d["node"] for d in designs}
    total = 0
    for d in designs:
        for card in d["children"]:
            path = ROOT.joinpath(*card["id"].split(".")).with_suffix(".py")
            if card["id"] in composite or not path.exists():
                continue
            own = {k.split(":", 1)[1]: v for k, v in contracts.items() if k.split(":", 1)[0] == card["id"]}
            problems, stats, (_, mc) = check_leaf(card, path, limits, overrides.get(card["id"], {}), own)
            total += len(problems)
            mark = "ок " if not problems else "НЕТ"
            sizes = "; ".join(f"{n}: {size}, сложность {cc}/{mc}" for n, size, cc in stats)
            print(f"{mark} {card['id']}  {sizes}")
            for p in problems:
                print("      ", p)
    print(f"\nнарушений Э1: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
