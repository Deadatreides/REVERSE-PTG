"""Затравка rptg.build: обвязка составных узлов по разложениям design/*.yaml (LOGIC §5, Э6).

Для каждого составного узла поддерева пишет пакет:
  __init__.py — операции узла в обёртках условий (requires на входе, ensures на выходе);
  _flows.py   — схемы потоков: вызов — вызов, отображение — генератор списка, свёртка — цикл,
                запись — конструктор dataclass;
  _leaves.py  — операции финальных детей в обёртках условий;
  _types.py   — типы, которыми владеет узел: запись — dataclass, остальное — псевдоним.
Условия переводит в Python сам rptg.lang: листья parse, typecheck, python и types.env
загружаются мимо __init__ пакетов, — скрипт собирает себя своими же листьями, и сборка с нуля
не зависит от прошлой сборки.

    python tools/codegen0.py rptg.lang           собрать поддерево rptg.lang
    python tools/codegen0.py rptg.lang --check   только сверить: не отстала ли обвязка от карты
"""
import importlib
import keyword
import sys
import types as pytypes
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

DESIGN = ROOT / "design"
PRIMITIVE_PY = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}
CHECK_ONLY = False


class Fail(Exception):
    pass


def attr(name):
    """Имя поля или параметра в Python: слово Python получает подчёркивание."""
    return name + "_" if keyword.iskeyword(name) else name


class Map:
    """Карточки, разложения и типы всей карты."""

    def __init__(self):
        root = design_io.load(DESIGN / "rptg.yaml")
        self.designs = {}
        for fname, d in design_io.designs(DESIGN):
            self.designs[d["node"]] = (d, f"design/{fname}")
        self.cards = {"rptg": root["card"]}
        for d, _ in self.designs.values():
            for c in d["children"]:
                self.cards[c["id"]] = c
        raw = yaml.safe_load((DESIGN / "types.yaml").read_text(encoding="utf-8"))
        self.typedefs = [{"name": n, "owner": "rptg", "doc": b.get("doc", ""), "schema": b["schema"]}
                         for n, b in raw.items()]
        for d, _ in self.designs.values():
            self.typedefs += [{"name": t["name"], "owner": t["owner"], "doc": t.get("doc", ""),
                               "schema": t["schema"]} for t in d.get("types") or []]
        self.owner = {t["name"]: t["owner"] for t in self.typedefs}
        self.schemas = {t["name"]: t["schema"] for t in self.typedefs}
        self.leaves = None

    def composite(self, node_id):
        return node_id in self.designs

    def module_of(self, type_name):
        return self.owner[type_name] + "._types"

    def ann(self, t, used):
        """Аннотация параметра по имени типа карточки."""
        if t in PRIMITIVE_PY:
            return PRIMITIVE_PY[t]
        if t.startswith("[") and t.endswith("]"):
            return f"list[{self.ann(t[1:-1], used)}]"
        if t not in self.owner:
            raise Fail(f"тип {t} не найден")
        if t == "Decimal":
            return "str"
        used.add(t)
        return t

    def imports(self, used, indent=""):
        by_module: dict = {}
        for t in sorted(used):
            by_module.setdefault(self.module_of(t), []).append(t)
        return [f"{indent}from {mod} import {', '.join(ts)}" for mod, ts in sorted(by_module.items())]

    def conds(self, node_id, op, side):
        """Условия операции: пары (текст CL, выражение Python)."""
        lv = self.leaves
        params = [{"name": p["name"], "type": p["type"]} for p in op["params"]]
        if side == "ensures":
            params.append({"name": "result", "type": op["result"]})
        made = lv.env(lv.load(lv.TypeDefs, self.typedefs), lv.load(lv.Params, params))
        if not made.ok:
            raise Fail(f"{node_id}:{op['name']}: окружение условий — {'; '.join(made.errors)}")
        out = []
        for text in op[side]:
            typed = lv.typecheck(lv.parse(text), made.env)
            if not typed.ok:
                raise Fail(f"{node_id}:{op['name']} {side} «{text}»: {'; '.join(typed.errors)}")
            out.append((text, lv.python(typed)))
        return out


# ── типы ─────────────────────────────────────────────────────────────────────
def camel(name):
    return "".join(part[:1].upper() + part[1:] for part in name.split("_"))


def types_module(m, node_id, note):
    """dataclasses записей и псевдонимы остального; имена предков — импортом (нужны во время работы)."""
    owned = [t for t in m.typedefs if t["owner"] == node_id]
    here = {t["name"] for t in owned}
    foreign, records, aliases = set(), [], []

    def py(s, hint):
        if not isinstance(s, dict) or not s or any(k in s for k in ("oneOf", "anyOf", "allOf")):
            return "Any"
        if "$ref" in s:
            if s["$ref"] not in here:
                foreign.add(s["$ref"])
            return s["$ref"]
        t = s.get("type")
        if t == "object" and "properties" in s:
            records.append((hint, s, ""))
            return hint
        if t == "object":
            extra = s.get("additionalProperties")
            return f"dict[str, {py(extra, hint + 'Value') if isinstance(extra, dict) else 'Any'}]"
        if t == "array":
            return f"list[{py(s.get('items', {}), hint + 'Item')}]"
        return PRIMITIVE_PY.get(t, "Any")

    for t in owned:
        s = t["schema"]
        if isinstance(s, dict) and s.get("type") == "object" and "properties" in s:
            records.append((t["name"], s, t["doc"]))
        else:
            aliases.append((t["name"], py(s, t["name"]), t["doc"]))
    body, i = [], 0
    while i < len(records):  # безымянные записи дописываются в очередь по ходу
        name, s, doc = records[i]
        i += 1
        body += ["", "", "@dataclass(kw_only=True)", f"class {name}:"]
        if doc:
            body.append(f'    """{doc}"""')
        for p, ps in s["properties"].items():
            ann = py(ps, name + camel(p))
            meta = f'metadata={{"json": {p!r}}}' if attr(p) != p else ""
            if p in s.get("required", []):
                body.append(f"    {attr(p)}: {ann}" + (f" = field({meta})" if meta else ""))
            else:
                body.append(f"    {attr(p)}: {ann} | None = " + (f"field(default=None, {meta})" if meta else "None"))
        if not s["properties"]:
            body.append("    pass")
    body += [""] + order_aliases(aliases, here)
    # схемы типов узла как данные: по ним проверки сверяют ответы моделей (П1) — лист не читает
    # файлы и не зовёт код проекта, а данные сгенерированных типов ему доступны (Э1)
    body += ["", "", "SCHEMAS: dict[str, Any] = {"]
    body += [f"    {t['name']!r}: {t['schema']!r}," for t in owned]
    body += ["}", '"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""']
    foreign -= here
    head = [f'"""{note}"""', "from __future__ import annotations", "",
            "from dataclasses import dataclass, field", "from typing import Any", ""]
    head += m.imports(foreign) + [""] if foreign else []
    return "\n".join(head + body).rstrip() + "\n"


def order_aliases(aliases, here):
    """Псевдонимы вычисляются при импорте: тот, на кого ссылаются, идёт раньше."""
    out, done, left = [], set(), list(aliases)
    names = {a[0] for a in aliases}
    while left:
        for a in left:
            deps = {n for n in names if n != a[0] and n in a[1].replace("[", " ").replace("]", " ").replace(",", " ").split()}
            if deps <= done:
                out += ["", f"{a[0]} = {a[1]}"] + ([f'"""{a[2]}"""'] if a[2] else [])
                done.add(a[0])
                left.remove(a)
                break
        else:
            raise Fail(f"цикл псевдонимов: {[a[0] for a in left]}")
    return out


# ── обёртки и схемы ──────────────────────────────────────────────────────────
def wrapper(m, node_id, op, impl, used, static):
    """Операция в обёртке условий: requires, вызов, ensures."""
    names = [p["name"] for p in op["params"]]
    for n in names + [op["name"]]:
        if keyword.iskeyword(n) or n in ("result", "_c"):
            raise Fail(f"{node_id}:{op['name']}: имя {n} занято в Python или в обёртке")
    sig = ", ".join(f"{p['name']}: {m.ann(p['type'], used)}" for p in op["params"])
    doc = op["doc"].replace('"""', "'''")
    lines = (["@staticmethod"] if static else []) + [
        f"def {op['name']}({sig}) -> {m.ann(op['result'], used)}:", f'    """{doc}"""']
    qual = f"{node_id}:{op['name']}"
    for side in ("requires", "ensures"):
        if side == "ensures":
            lines.append(f"    result = {impl}({', '.join(f'{n}={n}' for n in names)})")
        compiled = m.conds(node_id, op, side)
        if compiled:
            lines.append(f"    _c.check({qual!r}, {side!r}, [")
            lines += [f"        ({text!r}, lambda: {expr})," for text, expr in compiled]
            lines.append("    ])")
    lines.append("    return result")
    return lines


def refs_of(m, node_id, design):
    """Короткие имена в схемах → (псевдоним, строка импорта, карточка)."""
    table = {}
    for c in design["children"]:
        short = c["id"].rsplit(".", 1)[1]
        src = "." if m.composite(c["id"]) else "._leaves"
        table[short] = (f"c_{short}", f"from {src} import {short} as c_{short}", c)
    for u in m.cards[node_id].get("uses", []):
        # uses — братья узла или uses его родителя (§2.4), то есть узел может жить на любом уровне
        # выше: импорт абсолютный, от родителя u, а не «..» (так прочитался бы несуществующий брат)
        parent, short = u.rsplit(".", 1)
        src = parent if m.composite(u) else f"{parent}._leaves"
        table.setdefault(short, (f"u_{short}", f"from {src} import {short} as u_{short}", m.cards[u]))
    return table


def callee(table, ref, where):
    short, _, op = ref.partition(":")
    if short not in table:
        raise Fail(f"{where}: {ref} — нет такого ребёнка или узла uses")
    alias, _, card = table[short]
    ops = [o["name"] for o in card["ops"]]
    if not op and len(ops) != 1:
        raise Fail(f"{where}: {ref} — у узла несколько операций, нужно имя")
    op = op or ops[0]
    if op not in ops:
        raise Fail(f"{where}: у {card['id']} нет операции {op}")
    return short, f"{alias}.{op}", next(o for o in card["ops"] if o["name"] == op)


def source(s, known, where, item=None):
    """Источник → выражение Python. item — имя элемента отображения или свёртки (С-15): в коде
    это переменная цикла _x, поэтому имя элемента не заслоняет параметры и выходы схемы."""
    if isinstance(s, dict):
        return repr(s["const"])   # литерал JSON — и составной: он уходит в параметр своего типа
    head, *rest = s.split(".")
    if item is not None and head == item:
        head = "_x"
    elif head not in known:
        raise Fail(f"{where}: источник {s} не определён выше")
    return head + "".join("." + attr(f) for f in rest)


def as_json(expr, type_name):
    """Правило Json (map.md §12): значение, переданное в место типа Json, записывается в JSON."""
    return f"_v.dump({expr})" if type_name == "Json" else expr


def field_type(m, type_name, field):
    """Тип поля записи по схеме: имя типа, простой тип, [T] или Json; иначе None — не определить."""
    s = m.schemas.get(type_name)
    while isinstance(s, dict) and set(s) == {"$ref"}:
        s = m.schemas.get(s["$ref"])
    prop = ((s or {}).get("properties") or {}).get(field) if isinstance(s, dict) else None
    if not isinstance(prop, dict):
        return None
    if "$ref" in prop:
        return prop["$ref"]
    if prop.get("type") == "array" and isinstance(prop.get("items"), dict) and "$ref" in prop["items"]:
        return f"[{prop['items']['$ref']}]"
    return "Json" if not prop else prop.get("type") if prop.get("type") in PRIMITIVE_PY else None


def item_type(m, type_name):
    """Тип элемента списка: [T] — T, именованный список — тип его элементов; иначе None."""
    if type_name and type_name.startswith("[") and type_name.endswith("]"):
        return type_name[1:-1]
    s = m.schemas.get(type_name) if type_name else None
    items = s.get("items") if isinstance(s, dict) and s.get("type") == "array" else None
    return items.get("$ref") if isinstance(items, dict) else None


def source_type(m, s, known_types, item=None, item_t=None):
    """Тип источника схемы: параметр, выход узла или элемент — и путь по полям записей."""
    if isinstance(s, dict):
        return None
    head, *rest = s.split(".")
    t = item_t if item is not None and head == item else known_types.get(head)
    for f in rest:
        t = field_type(m, t, f) if t else None
    return t


def as_typed(expr, src, dst, records):
    """Правило Json в обратную сторону: значение типа Json, переданное в типизированное место (запись,
    список записей), приводится к типу места — _v.load проверяет его и бросает, если не подходит."""
    if src != "Json" or not dst or dst == "Json" or dst in PRIMITIVE_PY or dst == "Decimal":
        return expr
    if dst.startswith("[") and dst.endswith("]"):
        records.add(dst[1:-1])
        return f"_v.load(list[{dst[1:-1]}], {expr})"
    records.add(dst)
    return f"_v.load({dst}, {expr})"


def order(nodes, where):
    """Топологический порядок узлов схемы; при равенстве — порядок записи."""
    ids = {n["id"] for n in nodes}

    def deps(n):
        found = {n[k].split(".")[0] for k in ("over", "init") if isinstance(n.get(k), str)}
        for key in ("args", "fields"):
            found |= {v.split(".")[0] for v in (n.get(key) or {}).values() if isinstance(v, str)}
        return found & ids

    done, out = set(), []
    while len(out) < len(nodes):
        ready = [n for n in nodes if n["id"] not in done and deps(n) <= done]
        if not ready:
            raise Fail(f"{where}: цикл в схеме")
        out.append(ready[0])
        done.add(ready[0]["id"])
    return out


def flow(m, table, used_refs, records, name, op, fl, where):
    params = [p["name"] for p in op["params"]]
    known = set(params)
    types = {p["name"]: p["type"] for p in op["params"]}   # тип каждого имени схемы — для правила Json

    def put(s, dst, at, item=None, item_t=None):
        """Источник в место типа dst: в Json — записью JSON, из Json в запись — приведением."""
        expr = source(s, known, at, item)
        return as_json(expr, dst) if dst == "Json" else as_typed(expr, source_type(m, s, types, item, item_t), dst, records)

    lines = [f"def {name}({', '.join(params)}):"]
    for n in order(fl["nodes"], where):
        at = f"{where} {n['id']}"
        if "record" in n:
            records.add(n["record"])
            fields = ", ".join(f"{attr(k)}={put(v, field_type(m, n['record'], k), at)}" for k, v in n["fields"].items())
            lines.append(f"    {n['id']} = {n['record']}({fields})")
            types[n["id"]] = n["record"]
        else:
            short, fn, cop = callee(table, n.get("call") or n.get("map") or n.get("fold"), at)
            used_refs.add(short)
            ptypes = {p["name"]: p["type"] for p in cop["params"]}
            item, args = n.get("item"), n.get("args") or {}
            item_t = item_type(m, source_type(m, n["over"], types)) if "over" in n else None
            extra = "".join(f", {attr(k)}={put(v, ptypes.get(k), at, item, item_t)}" for k, v in args.items())
            # С-15: элемент питает параметр своего имени, если args его не заняли
            bind = f", {attr(item)}={put(item, ptypes.get(item), at, item, item_t)}" if item in ptypes and item not in args else ""
            if "call" in n:
                lines.append(f"    {n['id']} = {fn}({extra[2:]})")
            elif "map" in n:
                lines.append(f"    {n['id']} = [{fn}({(bind + extra)[2:]}) for _x in {source(n['over'], known, at)}]")
            else:
                lines.append(f"    {n['id']} = {put(n['init'], ptypes.get(n['acc']), at)}")
                lines.append(f"    for _x in {source(n['over'], known, at)}:")
                lines.append(f"        {n['id']} = {fn}({n['acc']}={n['id']}{bind}{extra})")
            types[n["id"]] = f"[{cop['result']}]" if "map" in n else cop["result"]
        known.add(n["id"])
    lines.append(f"    return {put(fl['result'], op['result'], where + ' result')}")
    return lines


def module(doc, runtime, body, used, m):
    """Модуль обвязки: условия могут звать Decimal, аннотации — только для проверки типов."""
    head = [f'"""{doc}"""', "from __future__ import annotations", ""]
    std = (["from decimal import Decimal"] if any("Decimal(" in line for line in body) else [])
    std += ["from typing import TYPE_CHECKING"] if used else []
    head += std + ([""] if std else []) + runtime + [""]
    if used:
        head += ["if TYPE_CHECKING:", *m.imports(used, "    "), ""]
    return "\n".join(head + body).rstrip() + "\n"


def build(m, node_id, written):
    design, src = m.designs[node_id]
    card = m.cards[node_id]
    pkg = ROOT.joinpath(*node_id.split("."))
    note = f"Сгенерировано tools/codegen0.py по {src} — не править руками."

    leaf_body, leaf_used, leaf_runtime = [], set(), ["from rptg import _contract as _c"]
    for c in design["children"]:
        if m.composite(c["id"]):
            continue
        short = c["id"].rsplit(".", 1)[1]
        path = pkg / f"{short}.py"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [o["name"] for o in c["ops"] if f"\ndef {o['name']}(" not in text]
        if missing:
            raise Fail(f"{c['id']}: нет кода листа ({path.relative_to(ROOT)}: {', '.join(missing)})")
        leaf_runtime.append(f"from . import {short} as _m_{short}")
        leaf_body += ["", "", f"class {short}:", f'    """Лист {c["id"]}: операции в обёртках условий."""']
        for o in c["ops"]:
            leaf_body.append("")
            leaf_body += ["    " + line if line else line
                          for line in wrapper(m, c["id"], o, f"_m_{short}.{o['name']}", leaf_used, True)]

    table = refs_of(m, node_id, design)
    ops = {o["name"]: o for o in card["ops"]}
    if set(ops) != set(design["flows"]):
        raise Fail(f"{node_id}: схемы {sorted(design['flows'])} не совпадают с операциями {sorted(ops)}")
    flows_body, used_refs, records = [], set(), set()
    for name in ops:
        flows_body += ["", ""] + flow(m, table, used_refs, records, name, ops[name], design["flows"][name],
                                      f"{src} {name}")
    flows_runtime = m.imports(records) + [table[s][1] for s in sorted(used_refs)]
    if any("_v.dump(" in line or "_v.load(" in line for line in flows_body):
        flows_runtime.insert(0, "from rptg import _values as _v")

    init_body, init_used = [], set()
    for o in card["ops"]:
        init_body += ["", ""] + wrapper(m, node_id, o, f"_flows.{o['name']}", init_used, False)

    files = {
        "__init__.py": module(f"{card['purpose']}\n\n{note}\n",
                              ["from rptg import _contract as _c", "", "from . import _flows"], init_body, init_used, m),
        "_flows.py": module(f"Схемы потоков узла {node_id}.\n\n{note}\n", flows_runtime, flows_body, set(), m),
        "_leaves.py": module(f"Финальные дети узла {node_id} в обёртках условий.\n\n{note}\n",
                             leaf_runtime, leaf_body, leaf_used, m),
    }
    for fname, text in files.items():
        write(pkg / fname, text, written)
    for c in design["children"]:
        if m.composite(c["id"]):
            build(m, c["id"], written)


def write(path, text, written):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        if not CHECK_ONLY:
            path.write_text(text, encoding="utf-8")
        written.append(str(path.relative_to(ROOT)))


def subtree(m, node_id):
    out = [node_id]
    for c in m.designs[node_id][0]["children"]:
        if m.composite(c["id"]):
            out += subtree(m, c["id"])
    return out


class Leaves:
    """Листья rptg.lang и сгенерированные типы — мимо __init__ пакетов: пакеты подменены пустыми."""

    def __init__(self, packages):
        for name in packages:
            stub = pytypes.ModuleType(name)
            stub.__path__ = [str(ROOT.joinpath(*name.split(".")))]
            sys.modules[name] = stub
        self.parse = importlib.import_module("rptg.lang.cl.parse").parse
        self.typecheck = importlib.import_module("rptg.lang.cl.typecheck").typecheck
        self.python = importlib.import_module("rptg.lang.cl.python").python
        self.env = importlib.import_module("rptg.lang.types").env
        self.load = importlib.import_module("rptg._values").load
        root = importlib.import_module("rptg._types")
        self.TypeDefs, self.Params = list[root.TypeDef], list[root.Param]


def main(argv):
    global CHECK_ONLY
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    CHECK_ONLY = "--check" in argv
    args = [a for a in argv[1:] if a != "--check"]
    target = args[0] if args else "rptg.lang"
    m = Map()
    if not m.composite(target):
        print(f"{target}: нет разложения")
        return 2
    written = []
    sys.path.insert(0, str(ROOT))
    try:
        nodes = ["rptg"] + [n for n in subtree(m, target) if n != "rptg"]
        for node_id in nodes:  # сначала типы: листья импортируют их во время работы
            src = "design/types.yaml" if node_id == "rptg" else m.designs[node_id][1]
            note = f"Типы, которыми владеет узел {node_id}.\n\nСгенерировано tools/codegen0.py по {src} — не править руками.\n"
            write(ROOT.joinpath(*node_id.split(".")) / "_types.py", types_module(m, node_id, note), written)
        packages = {".".join(n.split(".")[:i]) for n in nodes + ["rptg.lang.cl"] for i in range(1, n.count(".") + 2)}
        m.leaves = Leaves(sorted(packages))
        build(m, target, written)
    except Fail as e:
        print(f"НЕ СОБРАНО: {e}")
        return 1
    if CHECK_ONLY:
        print(f"сверено {target}: отстало файлов {len(written)}")
    else:
        print(f"собрано {target}: изменено файлов {len(written)}")
    for w in written:
        print("  ", w)
    return 1 if CHECK_ONLY and written else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
