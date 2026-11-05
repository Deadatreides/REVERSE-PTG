"""Прототип проверок rptg на собственной карте (design/).

Не продукт, а затравка для rptg.lang и rptg.check: разбор и вычисление CL,
П1 по типам, П7 на примерах, часть П2, связность схем потоков, заглушка П4
(совпадение условий после подстановки вместо Z3), априорные оценки и хэши.

    python tools/selfcheck.py          проверить и записать design/SELFCHECK.md
    python tools/selfcheck.py --fill   вписать хэши на места @@ИМЯ@@ в design/rptg.yaml
"""
import hashlib
import json
import keyword
import math
import re
import sys
from decimal import Decimal, DivisionByZero, InvalidOperation
from pathlib import Path

import jsonschema
import networkx as nx
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

DESIGN = ROOT / "design"
PRIMITIVES = {"string", "integer", "number", "boolean"}


# ── каноническая запись и хэш ────────────────────────────────────────────────
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def ancestors(node_id):
    parts = node_id.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts))]


def design_hash(state, node_id, design):
    """Хэш разложения: само разложение, карточка узла, карточки узлов uses и типы, которыми владеют
    строгие предки узла (map.md §7, С-9; §12, Н-9 — свои типы узла лежат в самом разложении)."""
    card = state["cards"][node_id]
    owners = set(ancestors(node_id))
    return digest({
        "design": design,
        "card": card,
        "uses": {u: state["cards"][u] for u in sorted(card.get("uses", []))},
        "types": {n: t for n, t in sorted(state["types"].items()) if t["owner"] in owners},
    })


def approval_hash(design, card, types):
    """Хэш утверждения (design/approvals.yaml): digest {разложение, карточка, типы}."""
    return digest({"design": design, "card": card, "types": types})


def approval_notes(rep, root, types_raw):
    """Совпадает ли последнее утверждение корня с картой: правка утверждённого снимает утверждение."""
    path = DESIGN / "approvals.yaml"
    if not path.exists():
        return
    last = [a for a in yaml.safe_load(path.read_text(encoding="utf-8")) or [] if a.get("node") == "rptg"][-1:]
    now = approval_hash(root["design"], root["card"], types_raw)
    if not last:
        rep.note(f"корень не утверждён; хэш для утверждения — `{now}`")
    elif last[0]["design_hash"] == now:
        rep.note(f"утверждение корня от {last[0]['date']} действует: хэш карты совпадает")
    else:
        rep.note(f"**утверждение корня от {last[0]['date']} снято правкой** — нужно новое; хэш сейчас `{now}`")


# ── язык условий CL ──────────────────────────────────────────────────────────
class ClError(Exception):
    pass


CRASHES = []  # сбои самих проверок (ERROR) — отдельно от нарушений карты


class DivZero(Exception):
    pass


TOKEN = re.compile(r"""\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<str>"(?:[^"\\]|\\.)*")|
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<op>=>|==|!=|<=|>=|[<>+\-*/%()\[\]{},.:]))""", re.X)
FUNCS = {"len", "abs", "min", "max", "startswith"}


def tokenize(text):
    out, pos = [], 0
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ClError(f"позиция {pos}: непонятный знак")
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


class Parser:
    def __init__(self, text):
        self.toks, self.i = tokenize(text), 0

    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else ("eof", None)

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def at(self, kind, val=None):
        t = self.peek()
        return t[0] == kind and (val is None or t[1] == val)

    def expect(self, kind, val=None):
        t = self.take()
        if t[0] != kind or (val is not None and t[1] != val):
            raise ClError(f"ожидалось {val or kind}, стоит {t[1]!r}")
        return t

    def parse(self):
        e = self.expr()
        if self.peek()[0] != "eof":
            raise ClError(f"лишнее в конце: {self.peek()[1]!r}")
        return e

    def expr(self):
        a = self.or_()
        if self.at("op", "=>"):
            self.take()
            return ("impl", a, self.expr())
        return a

    def or_(self):
        a = self.and_()
        while self.at("name", "or"):
            self.take()
            a = ("or", a, self.and_())
        return a

    def and_(self):
        a = self.not_()
        while self.at("name", "and"):
            self.take()
            a = ("and", a, self.not_())
        return a

    def not_(self):
        if self.at("name", "not"):
            self.take()
            return ("not", self.not_())
        return self.cmp()

    def cmp(self):
        a = self.arith()
        t = self.peek()
        if t[0] == "op" and t[1] in ("==", "!=", "<", "<=", ">", ">="):
            self.take()
            return ("cmp", t[1], a, self.arith())
        if self.at("name", "in"):
            self.take()
            return ("in", a, self.setlit() if self.at("op", "{") else self.path())
        return a

    def arith(self):
        a = self.term()
        while self.peek()[0] == "op" and self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            a = ("arith", op, a, self.term())
        return a

    def term(self):
        a = self.unary()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/", "%"):
            op = self.take()[1]
            a = ("arith", op, a, self.unary())
        return a

    def unary(self):
        if self.at("op", "-"):
            self.take()
            return ("neg", self.unary())
        return self.atom()

    def literal(self):
        t = self.take()
        if t[0] == "num":
            return ("num", Decimal(t[1]) if "." in t[1] else int(t[1]))
        if t[0] == "str":
            return ("str", json.loads(t[1]))
        if t == ("name", "true") or t == ("name", "false"):
            return ("bool", t[1] == "true")
        if t == ("name", "null"):
            return ("null",)
        if t == ("op", "-"):
            v = self.literal()
            return ("num", -v[1])
        raise ClError(f"ожидался литерал, стоит {t[1]!r}")

    def setlit(self):
        self.expect("op", "{")
        items = [self.literal()]
        while self.at("op", ","):
            self.take()
            items.append(self.literal())
        self.expect("op", "}")
        return ("set", items)

    def atom(self):
        t = self.peek()
        if t[0] in ("num", "str") or t in (("name", "true"), ("name", "false"), ("name", "null")):
            return self.literal()
        if t == ("op", "("):
            self.take()
            e = self.expr()
            self.expect("op", ")")
            return e
        if t[0] == "name":
            n = t[1]
            if n in ("forall", "exists"):
                self.take()
                var = self.expect("name")[1]
                self.expect("name", "in")
                p = self.path()
                self.expect("op", ":")
                return ("quant", n, var, p, self.expr())
            if n in ("sum", "count") and self.peek(1) == ("op", "("):
                self.take()
                self.take()
                e = self.expr()
                self.expect("name", "for")
                var = self.expect("name")[1]
                self.expect("name", "in")
                p = self.path()
                self.expect("op", ")")
                return ("agg", n, e, var, p)
            if n in FUNCS and self.peek(1) == ("op", "("):
                self.take()
                self.take()
                args = [self.expr()]
                while self.at("op", ","):
                    self.take()
                    args.append(self.expr())
                self.expect("op", ")")
                return ("func", n, args)
            return self.path()
        raise ClError(f"неожиданное {t[1]!r}")

    def path(self):
        name = self.expect("name")[1]
        steps = []
        while True:
            if self.at("op", "."):
                self.take()
                steps.append(("attr", self.expect("name")[1]))
            elif self.at("op", "["):
                self.take()
                steps.append(("idx", self.arith()))
                self.expect("op", "]")
            else:
                return ("path", name, steps)


def cl_parse(text):
    return Parser(text).parse()


DEC = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")


def as_num(v):
    if isinstance(v, bool):
        raise ClError("логическое там, где нужно число")
    if isinstance(v, (int, Decimal)):
        return Decimal(v)
    if isinstance(v, float):
        return Decimal(str(v))
    if isinstance(v, str) and DEC.match(v):
        return Decimal(v)
    raise ClError(f"не число: {v!r}")


def is_num(v):
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def coerce_pair(a, b):
    if is_num(a) and isinstance(b, str) and DEC.match(b):
        return as_num(a), as_num(b)
    if is_num(b) and isinstance(a, str) and DEC.match(a):
        return as_num(a), as_num(b)
    if is_num(a) and is_num(b):
        return as_num(a), as_num(b)
    return a, b


def truth(v):
    if not isinstance(v, bool):
        raise ClError(f"не логическое: {v!r}")
    return v


def cl_value(node, env):
    k = node[0]
    if k == "impl":
        return (not truth(cl_value(node[1], env))) or truth(cl_value(node[2], env))
    if k == "or":
        return truth(cl_value(node[1], env)) or truth(cl_value(node[2], env))
    if k == "and":
        return truth(cl_value(node[1], env)) and truth(cl_value(node[2], env))
    if k == "not":
        return not truth(cl_value(node[1], env))
    if k == "cmp":
        a, b = coerce_pair(cl_value(node[2], env), cl_value(node[3], env))
        op = node[1]
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if a is None or b is None:
            raise ClError("сравнение с null")
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    if k == "in":
        v = cl_value(node[1], env)
        c = cl_value(node[2], env)
        if isinstance(c, dict):
            return v in c
        return any(coerce_pair(v, x)[0] == coerce_pair(v, x)[1] for x in c)
    if k == "arith":
        a, b = as_num(cl_value(node[2], env)), as_num(cl_value(node[3], env))
        op = node[1]
        if op in ("/", "%") and b == 0:
            raise DivZero()
        return {"+": a + b, "-": a - b, "*": a * b, "/": a / b if op == "/" else 0, "%": a % b if op == "%" else 0}[op]
    if k == "neg":
        return -as_num(cl_value(node[1], env))
    if k in ("num", "str", "bool"):
        return node[1]
    if k == "null":
        return None
    if k == "set":
        return [cl_value(x, env) for x in node[1]]
    if k == "path":
        if node[1] not in env:
            raise ClError(f"неизвестное имя {node[1]}")
        v = env[node[1]]
        for step in node[2]:
            if step[0] == "attr":
                if v is None:
                    raise ClError(f"поле {step[1]} у null")
                if not isinstance(v, dict):
                    raise ClError(f"поле {step[1]} не у записи")
                v = v.get(step[1])
            else:
                i = int(as_num(cl_value(step[1], env)))
                if not isinstance(v, list) or not 0 <= i < len(v):
                    raise ClError(f"индекс {i} вне списка")
                v = v[i]
        return v
    if k == "func":
        args = [cl_value(a, env) for a in node[2]]
        n = node[1]
        if n == "len":
            return len(args[0])
        if n == "abs":
            return abs(as_num(args[0]))
        if n == "min":
            return min(as_num(a) for a in args)
        if n == "max":
            return max(as_num(a) for a in args)
        if n == "startswith":
            return str(args[0]).startswith(str(args[1]))
    if k == "quant":
        seq = cl_value(node[3], env)
        vals = (truth(cl_value(node[4], {**env, node[2]: x})) for x in seq)
        return all(vals) if node[1] == "forall" else any(vals)
    if k == "agg":
        seq = cl_value(node[4], env)
        if node[1] == "sum":
            return sum((as_num(cl_value(node[2], {**env, node[3]: x})) for x in seq), Decimal(0))
        return sum(1 for x in seq if truth(cl_value(node[2], {**env, node[3]: x})))
    raise ClError(f"узел {k}")


def cl_eval(text, values):
    """(ok, value, error): деление на ноль — ложь, а не ошибка (LOGIC §4.3)."""
    try:
        return True, truth(cl_value(cl_parse(text), values)), None
    except DivZero:
        return True, False, None
    except ClError as e:
        return False, None, str(e)


def cl_measure(node, bound=frozenset()):
    """(узлы, кванторы, нелинейность, свободные имена) — как в LOGIC §4.5."""
    k = node[0]
    if k == "path":
        names = set() if node[1] in bound else {node[1]}
        n, q, nl = 1, 0, 0
        for step in node[2]:
            if step[0] == "idx":
                a = cl_measure(step[1], bound)
                n, q, nl, names = n + a[0], q + a[1], nl + a[2], names | a[3]
        return n, q, nl, names
    if k in ("num", "str", "bool", "null", "set"):
        return 1, 0, 0, set()
    if k == "quant":
        p = cl_measure(node[3], bound)
        b = cl_measure(node[4], bound | {node[2]})
        return 1 + p[0] + b[0], 1 + p[1] + b[1], p[2] + b[2], p[3] | b[3]
    if k == "agg":
        p = cl_measure(node[4], bound)
        e = cl_measure(node[2], bound | {node[3]})
        return 1 + p[0] + e[0], 1 + p[1] + e[1], p[2] + e[2], p[3] | e[3]
    kids = [x for x in node[1:] if isinstance(x, tuple)] + [x for x in node[1:] if isinstance(x, list) for x in x]
    n, q, nl, names = 1, 0, 0, set()
    for c in kids:
        a = cl_measure(c, bound)
        n, q, nl, names = n + a[0], q + a[1], nl + a[2], names | a[3]
    if k == "arith" and node[1] in ("*", "/", "%") and node[2][0] != "num" and node[3][0] != "num":
        nl += 1
    return n, q, nl, names


def unparse(node, subst=None):
    """Каноническая запись условия с подстановкой голов путей — для заглушки П4."""
    subst = subst or {}
    k = node[0]
    u = lambda x: unparse(x, subst)
    if k == "path":
        steps = "".join(f".{s[1]}" if s[0] == "attr" else f"[{u(s[1])}]" for s in node[2])
        if node[1] in subst:
            return subst[node[1]] + steps
        return node[1] + steps
    if k == "quant":
        inner = {kk: vv for kk, vv in subst.items() if kk != node[2]}
        return f"({node[1]} {node[2]} in {u(node[3])}: {unparse(node[4], inner)})"
    if k == "agg":
        inner = {kk: vv for kk, vv in subst.items() if kk != node[3]}
        return f"{node[1]}({unparse(node[2], inner)} for {node[3]} in {u(node[4])})"
    if k in ("impl", "or", "and"):
        sym = {"impl": "=>", "or": "or", "and": "and"}[k]
        return f"({u(node[1])} {sym} {u(node[2])})"
    if k == "not":
        return f"(not {u(node[1])})"
    if k in ("cmp", "arith"):
        return f"({u(node[2])} {node[1]} {u(node[3])})"
    if k == "in":
        return f"({u(node[1])} in {u(node[2])})"
    if k == "neg":
        return f"(-{u(node[1])})"
    if k == "func":
        return f"{node[1]}({', '.join(u(a) for a in node[2])})"
    if k == "set":
        return "{" + ", ".join(u(x) for x in node[1]) + "}"
    if k == "num":
        return str(node[1])
    if k == "str":
        return json.dumps(node[1], ensure_ascii=False)
    if k == "bool":
        return "true" if node[1] else "false"
    if k == "null":
        return "null"
    raise ClError(k)


# ── типы ─────────────────────────────────────────────────────────────────────
def load_types():
    raw = yaml.safe_load((DESIGN / "types.yaml").read_text(encoding="utf-8"))
    return {name: body["schema"] for name, body in raw.items()}, raw


def to_jsonschema(schema):
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k == "$ref" and isinstance(v, str) and not v.startswith("#"):
                out[k] = f"#/$defs/{v}"
            else:
                out[k] = to_jsonschema(v)
        return out
    if isinstance(schema, list):
        return [to_jsonschema(x) for x in schema]
    return schema


def refs_in(schema):
    found = set()
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k == "$ref" and isinstance(v, str):
                found.add(v)
            else:
                found |= refs_in(v)
    elif isinstance(schema, list):
        for x in schema:
            found |= refs_in(x)
    return found


class Types:
    def __init__(self, schemas):
        self.schemas = schemas
        self.defs = {n: to_jsonschema(s) for n, s in schemas.items()}

    def exists(self, name):
        return name in PRIMITIVES or name in self.schemas

    def validate(self, value, name):
        if name in PRIMITIVES:
            schema = {"type": name}
        elif name in self.schemas:
            schema = {"$ref": f"#/$defs/{name}", "$defs": self.defs}
        else:
            return [f"тип {name} не найден"]
        try:
            errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.path))
        except Exception as e:
            # Сбой самой проверки — ERROR, а не нарушение предмета (arch0 SEAM_MODEL §4,
            # arch1 seam_engine): иначе баги проверки превращаются в ложные дефекты карты.
            CRASHES.append(f"проверка типа {name} упала: {type(e).__name__}")
            return []
        return [f"{'/'.join(map(str, e.path)) or '·'}: {e.message[:140]}" for e in errors[:3]]

    def size(self, name, depth=2, seen=()):
        if name in PRIMITIVES:
            return 1
        return self._size(self.schemas.get(name, {}), depth, seen + (name,))

    def _size(self, s, depth, seen):
        if not isinstance(s, dict):
            return 1
        if "$ref" in s:
            ref = s["$ref"]
            if depth <= 0 or ref in seen:
                return 1
            return self._size(self.schemas.get(ref, {}), depth - 1, seen + (ref,))
        n = 1
        for p in (s.get("properties") or {}).values():
            n += self._size(p, depth, seen)
        if isinstance(s.get("items"), dict):
            n += self._size(s["items"], depth, seen)
        if isinstance(s.get("additionalProperties"), dict):
            n += self._size(s["additionalProperties"], depth, seen)
        return n

    def list_item(self, name):
        """Тип элемента именованного списка: имя типа или простой тип; для "[T]" — T."""
        if name.startswith("[") and name.endswith("]"):
            return name[1:-1]
        s = self.schemas.get(name, {})
        items = s.get("items") if s.get("type") == "array" else None
        if isinstance(items, dict):
            if "$ref" in items:
                return items["$ref"]
            if items.get("type") in PRIMITIVES and len(items) == 1:
                return items["type"]
        return None

    def compatible(self, src, dst):
        """Тип источника подходит месту назначения: то же имя, списки одного элемента или место
        Json — любое значение подтип непрозрачного JSON, схема запишет объект в JSON (map.md §12).
        Источник Json — в любое место: обвязка приводит его к типу места (_v.load), а приведение
        проверяет значение и бросает, если оно не подходит (правило Json в обратную сторону, 01.10.2026,
        постройка plan: состояние внутри plan — JSON, как у check и build)."""
        if src == dst or dst == "Json" or src == "Json":
            return True
        s = self.schemas.get(src)
        while isinstance(s, dict) and set(s) == {"$ref"}:
            s = self.schemas.get(s["$ref"])
        if dst in PRIMITIVES and isinstance(s, dict) and s.get("type") == dst \
                and not {"properties", "items", "additionalProperties"} & set(s):
            return True   # именованный скаляр (Subject, Sha, Cl) — подтип своего простого типа
        a, b = self.list_item(src), self.list_item(dst)
        return a is not None and a == b


# ── сравнение примеров ───────────────────────────────────────────────────────
def subset_match(expected, actual):
    """Подмножество: словарь — указанные ключи, список — та же длина, "*" — любое значение."""
    if expected == "*":
        return True
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and subset_match(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(subset_match(e, a) for e, a in zip(expected, actual))
    return expected == actual


def has_wildcard(v):
    if v == "*":
        return True
    if isinstance(v, dict):
        return any(has_wildcard(x) for x in v.values())
    if isinstance(v, list):
        return any(has_wildcard(x) for x in v)
    return False


# ── априорная оценка (LOGIC §6.5) ────────────────────────────────────────────
def prior_design(card, types):
    ops = card["ops"]
    tsize = sum(types.size(p["type"]) for op in ops for p in op["params"]) + sum(types.size(op["result"]) for op in ops)
    nodes = quant = 0
    for op in ops:
        for c in op["requires"] + op["ensures"]:
            n, q, _, _ = cl_measure(cl_parse(c))
            nodes, quant = nodes + n, quant + q
    effects = len({e for op in ops for e in op["effects"]} | set(card["effects"]))
    text = (len(card["purpose"]) + sum(len(op["doc"]) for op in ops)) / 4
    f = {
        "ops": min(1, (len(ops) - 1) / 7), "types": min(1, tsize / 80), "cond": min(1, nodes / 120),
        "quant": min(1, quant / 6), "effects": min(1, effects / 3), "uses": min(1, len(card["uses"]) / 6),
        "size": min(1, card["est_lines"] / 1000), "text": min(1, text / 600),
    }
    w = {"ops": 3, "types": 2, "cond": 2, "quant": 1, "effects": 1, "uses": 2, "size": 4, "text": 2}
    return round(100 * sum(w[k] * f[k] for k in w) / sum(w.values())), f


def rung(score, bands):
    return 1 + sum(1 for b in bands if b <= score)


def mask_match(mask, node_id, level):
    if mask.startswith("level:"):
        lo, _, hi = mask[6:].partition("..")
        return int(lo) <= level <= int(hi or lo)
    if mask.endswith(".**"):
        base = mask[:-3]
        return node_id == base or node_id.startswith(base + ".")
    if mask.endswith(".*"):
        base = mask[:-2]
        return node_id.startswith(base + ".") and "." not in node_id[len(base) + 1:]
    return mask == node_id


# ── проверка ─────────────────────────────────────────────────────────────────
class Report:
    def __init__(self):
        self.errors, self.notes = [], []

    def err(self, where, text):
        self.errors.append(f"**{where}** — {text}")

    def note(self, text):
        self.notes.append(text)


def check(fill=False):
    """0 — нарушений нет; 1 — нарушения карты; 2 — сбой самой проверки (ERROR)."""
    CRASHES.clear()
    try:
        return _check(fill)
    except Exception as e:
        CRASHES.append(f"проверка упала целиком: {type(e).__name__}: {e}")
        (DESIGN / "SELFCHECK.md").write_text(
            "# Самопроверка карты rptg\n\n**ERROR: сбой самой проверки, вердикта о карте нет.**\n\n"
            + "\n".join(f"* {c}" for c in CRASHES) + "\n", encoding="utf-8")
        return 2


def fill_hashes(text, fx):
    values = {
        "D_APP": digest(fx["d_app"]),
        "D_APP_FIXED": digest(fx["d_app_fixed"]),
        "H_BILLING": design_hash(fx["s_billing"], "app.billing", fx["d_billing"]),
        "H_BILLING_FIXED": design_hash(fx["s_accept"], "app.billing", fx["d_billing"]),
        "D_FORM": digest(fx["e_form"]["answer"]["text"]),
        "D_BILLING_TEXT": digest(fx["billing_answer"]),
        "D_PREFIX": digest(fx["p_map"]["prefix"]),
    }
    for k, v in values.items():
        text = text.replace(f"@@{k}@@", v)
    (DESIGN / "rptg.yaml").write_text(text, encoding="utf-8")
    print("вписано:", ", ".join(f"{k}={v[:12]}…" for k, v in values.items()))
    return 0


def level_of(node_id):
    return node_id.count(".") + 1


def op_signature(op):
    return canonical({"params": [p["type"] for p in op["params"]], "result": op["result"],
                      "requires": op["requires"], "ensures": op["ensures"]})


def resolve_ref(ref, children, uses_cards):
    """Короткое имя операции в схеме: сначала дети, потом узлы uses (LOGIC §2.3)."""
    node_name, _, op_name = ref.partition(":")
    pool = [(c["id"].split(".")[-1], c) for c in children] + [(u["id"].split(".")[-1], u) for u in uses_cards]
    found = [c for short, c in pool if short == node_name]
    if len(found) != 1:
        return None, None, "не найдена" if not found else "неоднозначна"
    card = found[0]
    if not op_name:
        if len(card["ops"]) != 1:
            return None, None, "имя операции опущено, а операций у узла не одна"
        return card, card["ops"][0], None
    op = next((o for o in card["ops"] if o["name"] == op_name), None)
    return (card, op, None) if op else (None, None, "не найдена")


def schema_of(types, name):
    s = types.schemas.get(name, {})
    while isinstance(s, dict) and "$ref" in s and len(s) == 1:
        s = types.schemas.get(s["$ref"], {})
    return s


def field_type(types, type_name, field):
    """Тип поля записи: имя типа, простой тип или список [T]; «?» — не определить."""
    if not type_name or type_name == "?" or type_name.startswith("["):
        return "?"
    prop = (schema_of(types, type_name).get("properties") or {}).get(field)
    if not isinstance(prop, dict):
        return None
    if "$ref" in prop:
        return prop["$ref"]
    if prop.get("type") in PRIMITIVES and len(prop) <= 3:
        return prop["type"]
    if prop.get("type") == "array" and isinstance(prop.get("items"), dict) and "$ref" in prop["items"]:
        return f"[{prop['items']['$ref']}]"
    return "?"


def prior_impl(card, op, types, limits):
    """S_исп операции финального узла (LOGIC §6.5)."""
    nodes = quant = nonlin = 0
    for c in op["requires"] + op["ensures"]:
        n, q, nl, _ = cl_measure(cl_parse(c))
        nodes, quant, nonlin = nodes + n, quant + q, nonlin + nl
    tsize = sum(types.size(p["type"]) for p in op["params"]) + types.size(op["result"])
    size = card["est_lines"] / max(1, len(card["ops"]))
    text = (len(op["doc"]) + len(card["purpose"])) / 4
    f = {"cond": min(1, nodes / 60), "quant": min(1, quant / 4), "nonlin": min(1, nonlin / 2),
         "types": min(1, tsize / 40), "effects": min(1, len(op["effects"]) / 3),
         "size": min(1, size / limits["final_max_lines"]), "text": min(1, text / 300)}
    w = {"cond": 3, "quant": 2, "nonlin": 1, "types": 2, "effects": 1, "size": 3, "text": 1}
    return round(100 * sum(w[k] * f[k] for k in w) / sum(w.values()))


def route_child(child, project, types):
    """Вид узла по правилам LOGIC §6.2 и оператор по прикидке и ручным назначениям (§6.5, §6.6)."""
    lim, lvl = project["limits"], level_of(child["id"])
    manual = {}
    for mask, ov in project.get("overrides", {}).items():
        if mask_match(mask, child["id"], lvl):
            manual.update(ov)
    n_ops = len(child["ops"])
    if lvl >= lim["max_depth"]:
        kind, rule = "финальный", 2
    elif child["uses"]:
        kind, rule = "составной", 3
    elif n_ops > lim["final_max_ops"]:
        kind, rule = "составной", 4
    elif manual.get("kind"):
        kind, rule = ("финальный" if manual["kind"] == "final" else "составной"), 5
    elif child["est_lines"] > lim["final_max_lines"] * n_ops:
        kind, rule = "составной", 6
    else:
        kind, rule = "финальный", 7
    if kind == "составной":
        role, score = "designer", prior_design(child, types)[0]
    else:
        role, score = "implementer", max(prior_impl(child, op, types, lim) for op in child["ops"])
    ladder = project["roles"][role]
    operator = ladder[min(rung(score, project["routing"]["prior_bands"][role]), len(ladder)) - 1]
    by = "прикидка"
    if role in manual:
        operator, by = manual[role], "ручное"
    if rule == 5:
        by += ", вид — ручной"
    return (child["id"], lvl, kind, rule, n_ops, child["est_lines"],
            ", ".join(u.split(".")[-1] for u in child["uses"]) or "—", score, operator, by)


def _check(fill):
    rep = Report()
    root_text = (DESIGN / "rptg.yaml").read_text(encoding="utf-8")
    root = yaml.safe_load(root_text)
    fx = root.get("fixtures") or {}
    if fill:
        return fill_hashes(root_text, fx)
    project = yaml.safe_load((DESIGN / "project.yaml").read_text(encoding="utf-8"))
    designs = design_io.designs(DESIGN)

    schemas, _ = load_types()
    approval_notes(rep, root, yaml.safe_load((DESIGN / "types.yaml").read_text(encoding="utf-8")))
    for fname, d in designs:
        for t in d.get("types") or []:
            if t["name"] in schemas:
                rep.err(fname, f"I2: тип {t['name']} уже объявлен")
            if t["owner"] != d["node"]:
                rep.err(fname, f"владелец типа {t['name']} — {t['owner']}, а разложение узла {d['node']}")
            schemas[t["name"]] = t["schema"]
    types = Types(schemas)
    stats = {"types": len(schemas), "designs": len(designs), "ops": 0, "conds": 0, "examples": 0,
             "exact": 0, "subset": 0, "ensures_checked": 0}

    # 1. типы: ссылки разрешаются
    for name, schema in schemas.items():
        for r in refs_in(schema):
            if r not in schemas:
                rep.err(f"тип {name}", f"ссылка на неизвестный тип {r}")

    # 2. П1: карточка корня и каждое разложение — по типам метода
    for e in types.validate(root["card"], "NodeCard"):
        rep.err("карточка rptg", f"П1 NodeCard: {e}")
    for fname, d in designs:
        for e in types.validate(d, "Design"):
            rep.err(fname, f"П1 Design: {e}")

    # 3. места для хэшей заполнены
    left = sorted(set(re.findall(r"@@([A-Z_]+)@@", root_text)))
    if left:
        rep.err("rptg.yaml", f"не вписаны хэши: {', '.join(left)} — запустите с --fill")

    cards = {"rptg": root["card"]}
    for fname, d in designs:
        for c in d["children"]:
            if c["id"] in cards:
                rep.err(fname, f"I2: узел {c['id']} описан дважды")
            cards[c["id"]] = c

    # 4. операции: типы, условия, примеры (П1, П7)
    all_ops = [("rptg", op, True) for op in root["card"]["ops"]]
    all_ops += [(c["id"], op, False) for _, d in designs for c in d["children"] for op in c["ops"]]
    for node_id, op, is_root in all_ops:
        stats["ops"] += 1
        check_op(rep, stats, types, node_id, op, is_root)

    # 5. П2 и схемы — для каждого разложения на любой глубине одинаково
    called, rows = set(), []
    p4 = {"proved": 0, "total": 0, "left": []}
    p5 = {"proved": 0, "total": 0, "left": []}
    for fname, d in designs:
        node = d["node"]
        card = cards.get(node)
        if card is None:
            rep.err(fname, f"нет карточки узла {node}: его разложение не с чем сверять")
            continue
        check_structure(rep, fname, node, card, d, project)
        check_flows(rep, node, card, d, cards, types, called, p4, p5)
        rows += [route_child(c, project, types) for c in d["children"]]

    # 6. согласованность данных примеров корня (сквозной пример накладных)
    if {"billing_answer", "d_billing"} <= set(fx):
        try:
            answer = json.loads(fx["billing_answer"])
            if answer != {k: v for k, v in fx["d_billing"].items() if k != "node"}:
                rep.err("fixtures", "текст ответа конструктора не совпадает с d_billing")
        except json.JSONDecodeError as e:
            rep.err("fixtures", f"ответ конструктора — не JSON: {e}")
    if {"s_accept", "d_billing", "evs_fixed"} <= set(fx):
        h = design_hash(fx["s_accept"], "app.billing", fx["d_billing"])
        if any(ev["subject_hash"] != h for ev in fx["evs_fixed"]):
            rep.err("fixtures", "хэш разложения в примере приёмки не совпадает с правилом хэша")

    # 7. операции, которых не вызывает ни одна схема (I10 проверяется в конце разложения)
    not_called = [f"{nid}:{o['name']}" for nid, c in cards.items() if nid != "rptg"
                  for o in c["ops"] if f"{nid}:{o['name']}" not in called]

    write_report(rep, stats, rows, not_called, p4, p5)
    return 2 if CRASHES else (1 if rep.errors else 0)


def check_op(rep, stats, types, node_id, op, is_root):
    where = f"{node_id}:{op['name']}"
    pnames = [p["name"] for p in op["params"]]
    for p in op["params"]:
        # result — имя результата в ensures (LOGIC §4.1): параметр с этим именем делает условие
        # неоднозначным; слово Python не станет именем параметра в сгенерированном коде
        if p["name"] == "result" or keyword.iskeyword(p["name"]):
            rep.err(where, f"П1: имя параметра {p['name']} занято (result или слово Python)")
        if not types.exists(p["type"]):
            rep.err(where, f"тип параметра {p['name']} — {p['type']} не найден")
    if not types.exists(op["result"]):
        rep.err(where, f"тип результата {op['result']} не найден")
    for kind in ("requires", "ensures"):
        for c in op[kind]:
            stats["conds"] += 1
            try:
                ast = cl_parse(c)
            except ClError as e:
                rep.err(where, f"условие не разбирается: «{c}» — {e}")
                continue
            free = cl_measure(ast)[3]
            allowed = set(pnames) | ({"result"} if kind == "ensures" else set())
            if free - allowed:
                rep.err(where, f"в «{c}» имена вне параметров: {', '.join(sorted(free - allowed))}")
    exs = op["examples"]
    need = 2 if is_root else 1
    if len(exs) < need:
        rep.err(where, f"I15: примеров {len(exs)}, нужно не меньше {need}")
    if is_root and not any(e["source"] == "user" for e in exs):
        rep.err(where, "I15: у операции корня нет ни одного примера пользователя")
    for i, ex in enumerate(exs, 1):
        stats["examples"] += 1
        tag = f"{where} пример {i}"
        match = ex.get("match", "exact")
        stats[match] += 1
        if not isinstance(ex["in"], dict) or set(ex["in"]) != set(pnames):
            rep.err(tag, f"П7: вход {sorted(ex['in']) if isinstance(ex['in'], dict) else ex['in']} не совпадает с параметрами {pnames}")
            continue
        for p in op["params"]:
            for e in types.validate(ex["in"][p["name"]], p["type"]):
                rep.err(tag, f"П7: вход {p['name']} не проходит {p['type']}: {e}")
        if match == "exact":
            if has_wildcard(ex["out"]):
                rep.err(tag, "П7: «*» разрешена только в сравнении по подмножеству")
            for e in types.validate(ex["out"], op["result"]):
                rep.err(tag, f"П7: выход не проходит {op['result']}: {e}")
        for c in op["requires"]:
            ok, val, err = cl_eval(c, ex["in"])
            if not ok:
                rep.err(tag, f"П7: requires «{c}» не вычисляется: {err}")
            elif not val:
                rep.err(tag, f"П7: requires «{c}» ложно на входе")
        if match == "exact":
            for c in op["ensures"]:
                stats["ensures_checked"] += 1
                ok, val, err = cl_eval(c, {**ex["in"], "result": ex["out"]})
                if not ok:
                    rep.err(tag, f"П7: ensures «{c}» не вычисляется: {err}")
                elif not val:
                    rep.err(tag, f"П7: ensures «{c}» ложно")


def check_structure(rep, fname, node, card, d, project):
    """П2 для разложения узла: I1, I3, I8, I9, I11, I17, I18."""
    lim = project["limits"]
    children = {c["id"]: c for c in d["children"]}
    if len(children) > lim["max_children"]:
        rep.err(fname, f"I3: детей {len(children)} > {lim['max_children']}")
    parent_sig = sorted(op_signature(o) for o in card["ops"])
    g = nx.DiGraph()
    for cid, c in children.items():
        g.add_node(cid)
        if level_of(cid) != level_of(node) + 1 or not cid.startswith(node + "."):
            rep.err(cid, f"I1: путь узла не продолжает путь родителя {node}")
        if level_of(cid) > lim["max_depth"]:
            rep.err(cid, f"I1: уровень {level_of(cid)} > max_depth {lim['max_depth']}")
        if c.get("parent") != node or c["owner"] != node:
            rep.err(cid, f"I1/I17: родитель и владелец обязаны быть {node}")
        if c["est_lines"] >= card["est_lines"]:
            rep.err(cid, f"I11: est_lines {c['est_lines']} не меньше, чем у родителя ({card['est_lines']})")
        if sorted(op_signature(o) for o in c["ops"]) == parent_sig:
            rep.err(cid, "I11: ребёнок повторяет весь интерфейс родителя")
        if not set(c["effects"]) <= set(card["effects"]):
            rep.err(cid, "I18: эффекты шире родительских")
        extra = set(c["allowed_imports"]) - set(card["allowed_imports"])
        if extra:
            rep.err(cid, f"I18: импорты шире родительских: {sorted(extra)}")
        for u in c["uses"]:
            if u in children:
                g.add_edge(cid, u)
            elif u not in card["uses"]:
                rep.err(cid, f"I8: uses {u} — не брат и не из uses родителя")
        if level_of(cid) == lim["max_depth"] and (c["uses"] or len(c["ops"]) > lim["final_max_ops"]):
            rep.err(cid, "I8: узел на max_depth обязан уметь быть финальным")
    for cyc in nx.simple_cycles(g):
        rep.err(fname, f"I9: цикл зависимостей {' → '.join(cyc)}")


def check_flows(rep, node, card, d, cards, types, called, p4, p5):
    """Связность схем (I4–I7), П3, заглушки П4 и П5 для разложения узла."""
    children = d["children"]
    uses_cards = [cards[u] for u in card["uses"] if u in cards]
    own_ops = {op["name"]: op for op in card["ops"]}
    flows = d.get("flows") or {}
    for name in own_ops:
        if name not in flows:
            rep.err(f"{node}:{name}", "I4: нет схемы потока")
    for name in flows:
        if name not in own_ops:
            rep.err(f"{node}, схема {name}", "нет такой операции у узла")
    for fname, flow in flows.items():
        op = own_ops.get(fname)
        if not op:
            continue
        params = {p["name"]: p["type"] for p in op["params"]}
        out_type, maps, used, records = {}, {}, set(), {}
        facts = {unparse(cl_parse(c)) for c in op["requires"]}
        where0 = f"{node}, схема {fname}"

        def src_type(src, where, local=None):
            if isinstance(src, dict):
                return None
            head = re.split(r"[.\[]", src, 1)[0]
            rest = src[len(head):]
            if local and head in local:   # элемент отображения или свёртки (С-15)
                t = local[head]
                if t in (None, "?"):
                    return "?"
            elif head in params:
                t = params[head]
            elif head in out_type:
                used.add(head)
                t = out_type[head]
            else:
                rep.err(where, f"источник {src} не найден")
                return None
            if not rest:
                return t
            if "[" in rest:
                return "?"
            for f in rest.strip(".").split("."):
                t = field_type(types, t, f)
                if t is None:
                    rep.err(where, f"у источника {src} нет поля {f}")
                    return None
                if t == "?":
                    return "?"
            return t

        for n in flow["nodes"]:
            where = f"{where0}, узел {n['id']}"
            kinds = [k for k in ("call", "map", "fold", "record") if k in n]
            if len(kinds) != 1:
                rep.err(where, "ровно одно из call, map, fold, record")
                continue
            kind = kinds[0]
            if kind == "record":
                tname = n["record"]
                s = schema_of(types, tname)
                if not s:
                    rep.err(where, f"тип записи {tname} не найден")
                    continue
                props, req = s.get("properties") or {}, set(s.get("required") or [])
                fields = n.get("fields") or {}
                for f in set(fields) - set(props):
                    rep.err(where, f"у {tname} нет поля {f}")
                for f in req - set(fields):
                    rep.err(where, f"обязательное поле {tname}.{f} не заполнено")
                for f, src in fields.items():
                    st, pt = src_type(src, where), field_type(types, tname, f)
                    if st and st != "?" and pt and pt != "?" and not types.compatible(st, pt):
                        rep.err(where, f"П3: {src} ({st}) → {tname}.{f} ({pt})")
                records[n["id"]] = fields
                out_type[n["id"]] = tname
                continue
            ccard, cop, why = resolve_ref(n[kind], children, uses_cards)
            if not cop:
                rep.err(where, f"операция {n[kind]} {why}")
                continue
            called.add(f"{ccard['id']}:{cop['name']}")
            cparams = {p["name"]: p["type"] for p in cop["params"]}
            args = n.get("args") or {}
            fed = set(args)
            local, elem = {}, set()
            if kind in ("map", "fold"):
                # С-15: item — имя элемента в пределах узла; параметр того же имени, не занятый
                # args, питается элементом; args могут брать поля элемента (item.поле)
                item = n["item"]
                if item in params or item in {m["id"] for m in flow["nodes"]}:
                    rep.err(where, f"I5: имя элемента {item} совпадает с параметром или узлом схемы")
                over_t = src_type(n["over"], where)
                item_t = types.list_item(over_t) if over_t and over_t != "?" else "?"
                if item_t is None:
                    rep.err(where, f"П3: {n['over']} ({over_t}) — не список")
                local = {item: item_t}
                if item in cparams and item not in args:
                    fed.add(item)
                    elem.add(item)
                    if item_t not in (None, "?") and not types.compatible(item_t, cparams[item]):
                        what = "отображение" if kind == "map" else "свёртка"
                        rep.err(where, f"П3: {what} по {over_t}, а параметр {item} — {cparams[item]}")
                elem |= {pn for pn, src in args.items()
                         if isinstance(src, str) and re.split(r"[.\[]", src, 1)[0] == item}
            if kind == "map":
                maps[n["id"]] = n["over"]
            if kind == "fold":
                fed.add(n["acc"])
                elem.add(n["acc"])
                init_t = src_type(n["init"], where)
                if init_t and init_t != "?" and not types.compatible(init_t, cparams.get(n["acc"], "")):
                    rep.err(where, f"П3: начальное значение {init_t}, а накопитель — {cparams.get(n['acc'])}")
            if fed != set(cparams):
                rep.err(where, f"I5: питаются {sorted(fed)}, у {n[kind]} параметры {sorted(cparams)}")
            subst = {}
            for pn, src in args.items():
                st, pt = src_type(src, where, local), cparams.get(pn)
                if st and st != "?" and pt and not types.compatible(st, pt):
                    rep.err(where, f"П3: {src} ({st}) → {pn} ({pt})")
                subst[pn] = src if isinstance(src, str) else json.dumps(src.get("const"), ensure_ascii=False)
            for c in cop["requires"]:
                ast = cl_parse(c)
                p4["total"] += 1
                if elem & cl_measure(ast)[3]:
                    p4["left"].append(f"`{node}.{fname}.{n['id']}`: «{c}» — поэлементно, нужен Z3")
                    continue
                ob = map_len(unparse(ast, subst), maps)
                if ob in {map_len(f, maps) for f in facts} or trivially_true(ob):
                    p4["proved"] += 1
                else:
                    p4["left"].append(f"`{node}.{fname}.{n['id']}`: «{c}» → `{ob}`")
            if kind == "call":
                for c in cop["ensures"]:
                    facts.add(unparse(cl_parse(c), {**subst, "result": n["id"]}))
            out_type[n["id"]] = f"[{cop['result']}]" if kind == "map" else cop["result"]
        res = flow["result"]
        rt = src_type(res, f"{where0}, результат")
        if rt and rt != "?" and not types.compatible(rt, op["result"]):
            rep.err(where0, f"П3: результат {rt}, а операция возвращает {op['result']}")
        for nid in out_type:
            if nid not in used and nid != res:
                rep.err(where0, f"I6: выход {nid} не используется")
        for c in op["ensures"]:
            p5["total"] += 1
            ob = map_len(unparse(cl_parse(c), {"result": res}), maps)
            if res in records:   # результат — запись: поле result.f заменяется своим источником
                for f, src in records[res].items():
                    if isinstance(src, str):
                        ob = ob.replace(f"{res}.{f}", src)
            if ob in {map_len(f, maps) for f in facts} or trivially_true(ob):
                p5["proved"] += 1
            else:
                p5["left"].append(f"`{node}.{fname}`: «{c}»")


def map_len(text, maps):
    for nid, over in maps.items():
        text = text.replace(f"len({nid})", f"len({over})")
    return text


def trivially_true(text):
    m = re.fullmatch(r"\((.+) == (.+)\)", text)
    return bool(m and m.group(1) == m.group(2))


def write_report(rep, stats, rows, not_called, p4, p5):
    ok = not rep.errors
    verdict = "нарушений нет" if ok else f"нарушений {len(rep.errors)}"
    if CRASHES:
        verdict = f"ERROR — сбоев самой проверки {len(CRASHES)}; вердикт о карте неполон"
    lines = [
        "# Самопроверка карты rptg",
        "",
        "Сгенерировано `tools/selfcheck.py`. Это прототип проверок, а не rptg: П4 и П5 здесь —",
        "заглушка (совпадение условий после подстановки), настоящие доказательства даст Z3.",
        "Контрольные случаи прототипа четырёх видов — `tools/selfcheck_cases.py`.",
        "",
        f"**Итог: {verdict}.**",
        "",
        "| что | сколько |",
        "|---|---|",
        f"| разложений (корень и ниже) | {stats['designs']} |",
        f"| типов | {stats['types']} |",
        f"| операций | {stats['ops']} |",
        f"| условий, разобрано CL | {stats['conds']} |",
        f"| примеров | {stats['examples']} (точных {stats['exact']}, по подмножеству {stats['subset']}) |",
        f"| гарантий, вычисленных на точных примерах | {stats['ensures_checked']} |",
        f"| обязательств П4 доказано заглушкой | {p4['proved']} из {p4['total']} |",
        f"| гарантий П5 выведено заглушкой | {p5['proved']} из {p5['total']} |",
        "",
    ]
    if CRASHES:
        lines += ["## Сбои самой проверки (ERROR, не нарушения карты)", ""] + [f"* {c}" for c in CRASHES] + [""]
    if rep.errors:
        lines += ["## Нарушения", ""] + [f"* {e}" for e in rep.errors] + [""]
    lines += [
        "## Маршрутизация узлов",
        "",
        "Вид узла — LOGIC §6.2, прикидка — §6.5 (S_раз для составных, S_исп для финальных),",
        "назначения — `design/project.yaml`.",
        "",
        "| узел | уровень | вид | правило | операций | est_lines | uses | прикидка | оператор | почему |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ] + [f"| `{r[0]}` | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} |" for r in rows] + [""]
    if p4["left"] or p5["left"]:
        lines += ["## Что заглушка П4/П5 не вывела — ждёт Z3", ""] + [f"* {x}" for x in p4["left"] + p5["left"]] + [""]
    lines += [
        "## Операции, которых пока не вызывает ни одна схема",
        "",
        "Их вызовут схемы ещё не разложенных подсистем. I10 (достижимость) проверяется, когда разложено",
        "всё дерево.",
        "",
        ", ".join(f"`{x}`" for x in not_called) or "—",
        "",
    ]
    if rep.notes:
        lines += ["## Заметки", ""] + [f"* {n}" for n in rep.notes] + [""]
    (DESIGN / "SELFCHECK.md").write_text("\n".join(lines), encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines[:18]))
    if rep.errors:
        print("\n".join(rep.errors[:40]))


if __name__ == "__main__":
    sys.exit(check(fill="--fill" in sys.argv))
