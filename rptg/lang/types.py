"""Лист rptg.lang.types — язык типов: окружение, тип по пути, подтип, проверка значения, размер.

Функции приняты по карточке design/rptg.lang.yaml; обвязку пишет скрипт.
Имя типа — простой тип (string, integer, number, boolean), имя из окружения или [T] — список T.
Схемы — JSON Schema, ссылка на тип — {$ref: Имя}.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import jsonschema

from rptg._types import EnvResult, PathType, SubResult, TypeEnv, Validation

if TYPE_CHECKING:
    from rptg._types import Json, Params, TypeDefs


def env(types: TypeDefs, vars: Params) -> EnvResult:
    """Окружение: схемы типов, достижимых из переменных по ссылкам, и типы переменных.

    Decimal и Json встроены в язык (LOGIC §4.2): если проект их не объявил, окружение берёт их
    схемы отсюда.
    """
    defs = {"Decimal": {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}, "Json": {}}
    errors: list = []
    seen: set = set()
    for t in types:
        if t.name in seen:
            errors.append(f"тип {t.name} объявлен дважды")
        seen.add(t.name)
        defs[t.name] = t.schema
    out: dict = {}

    def refs(s):
        if isinstance(s, dict):
            here = [v for k, v in s.items() if k == "$ref" and isinstance(v, str)]
            return here + [r for k, v in s.items() if k != "$ref" for r in refs(v)]
        return [r for x in s for r in refs(x)] if isinstance(s, list) else []

    def need(name, where):
        while name.startswith("[") and name.endswith("]"):
            name = name[1:-1]
        if name in ("string", "integer", "number", "boolean") or name in out:
            return
        if name not in defs:
            errors.append(f"{where}: тип {name} не найден")
            return
        out[name] = defs[name]
        for r in refs(defs[name]):
            need(r, name)

    for p in vars:
        need(p.type, p.name)
    return EnvResult(ok=not errors, env=TypeEnv(types=out, vars={p.name: p.type for p in vars}), errors=errors)


def path(root: str, path: str, env: TypeEnv) -> PathType:
    """Тип значения по пути внутри типа: поля через точку, элемент списка — [] или [номер].

    Если на конце пути ссылка, name — имя типа, schema — его схема.
    """
    types = env.types

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        if t.startswith("[") and t.endswith("]"):
            return {"type": "array", "items": named(t[1:-1])}
        return {"$ref": t}

    def resolve(s):
        seen = set()
        while "$ref" in s and s["$ref"] not in seen:
            if s["$ref"] not in types:
                return None
            seen.add(s["$ref"])
            s = types[s["$ref"]]
        return s

    s = named(root)
    for part in path.split(".") if path else []:
        field, lists = part.split("[")[0], part.count("[")
        for kind, key in ([("properties", field)] if field else []) + [("items", "")] * lists:
            body = resolve(s)
            if body is None:
                return PathType(ok=False, schema={}, error=f"тип {s['$ref']} не найден")
            nxt = body.get("properties", {}).get(key) if kind == "properties" else body.get("items")
            if not isinstance(nxt, dict):
                return PathType(ok=False, schema={}, error=f"в {root} нет пути {path}")
            s = nxt
    body = resolve(s)
    if body is None:
        return PathType(ok=False, schema={}, error=f"тип {s['$ref']} не найден")
    return PathType(ok=True, name=s["$ref"], schema=body) if "$ref" in s else PathType(ok=True, schema=s)


def sub(a: str, b: str, env: TypeEnv) -> SubResult:
    """Тип a — подтип b: любое значение a проходит b. Если нет — свидетель.

    «Да» — когда следует из схем; свидетель проходит a и не проходит b; «нет» без него — «не доказано».
    """
    types = env.types
    known = {"type", "enum", "pattern", "minimum", "maximum", "minLength", "maxLength", "minItems",
             "maxItems", "items", "properties", "required", "additionalProperties", "doc", "description"}
    bounds = [("minimum", 1), ("minLength", 1), ("minItems", 1), ("maximum", -1), ("maxLength", -1), ("maxItems", -1)]

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        return {"type": "array", "items": named(t[1:-1])} if t.startswith("[") else {"$ref": t}

    def res(s):
        seen = set()
        while "$ref" in s and s["$ref"] in types and s["$ref"] not in seen:  # кольцо псевдонимов A → B → A
            seen.add(s["$ref"])
            s = types[s["$ref"]]
        return s

    def kinds_ok(x, y):
        tx, ty = x.get("type"), y.get("type")
        return not set(y) - known and "$ref" not in x and "$ref" not in y and (tx == ty or (tx, ty) == ("integer", "number"))

    def values_ok(x, y):
        enum_ok = "enum" not in y or all(v in y["enum"] for v in x.get("enum", [None]))
        pattern_ok = "pattern" not in y or x.get("pattern") == y["pattern"]
        return enum_ok and pattern_ok and all(k not in y or (k in x and (x[k] - y[k]) * sign >= 0) for k, sign in bounds)

    def object_le(x, y, seen):
        xp, yp, extra = x.get("properties", {}), y.get("properties", {}), y.get("additionalProperties", True)
        if not set(y.get("required", [])) <= set(x.get("required", [])) or not all(le(xp.get(p, {}), v, seen) for p, v in yp.items()):
            return False
        rest = [v for p, v in xp.items() if p not in yp] + [x.get("additionalProperties", True)]
        return extra is True or all(r is False or (extra is not False and r is not True and le(r, extra, seen)) for r in rest)

    def le(x, y, seen):
        key = (x.get("$ref"), y.get("$ref"))
        if x == y or res(y) == {} or (None not in key and key in seen):
            return True
        seen, x, y = seen | {key}, res(x), res(y)
        if not (kinds_ok(x, y) and values_ok(x, y)):
            return False
        if x.get("type") == "array":
            return le(x.get("items", {}), y.get("items", {}), seen)
        return object_le(x, y, seen) if x.get("type") == "object" else True

    def fix(s):
        if isinstance(s, dict):
            return {k: (f"#/$defs/{v}" if k == "$ref" and isinstance(v, str) else fix(v)) for k, v in s.items()}
        return [fix(v) for v in s] if isinstance(s, list) else s

    sa, sb = named(a), named(b)
    if le(sa, sb, frozenset()):
        return SubResult(ok=True)
    if "$ref" in res(sa) or "$ref" in res(sb):  # неизвестный тип или кольцо — свидетеля не искать
        return SubResult(ok=False)
    good, bad = (jsonschema.Draft202012Validator(fix({**s, "$defs": types})) for s in (sa, sb))
    for v in [0, 1, -1, 0.5, "", "a", True, None, [], {}, [0], ["a"], {"a": 0}]:
        if good.is_valid(v) and not bad.is_valid(v):
            return SubResult(ok=False, witness=v)
    return SubResult(ok=False)


def validate(value: Json, type: str, env: TypeEnv) -> Validation:
    """Проверить значение по типу (JSON Schema 2020-12, ссылки — на типы окружения).

    Неизвестный тип — нарушение с причиной. Сбой самой проверки (например, неверное регулярное
    выражение в схеме) — исключение, а не нарушение: ошибка проверки не должна стать дефектом
    проверяемого (arch0 SEAM_MODEL §4).
    """
    types = env.types

    def fix(s):
        if isinstance(s, dict):
            return {k: (f"#/$defs/{v}" if k == "$ref" and isinstance(v, str) else fix(v)) for k, v in s.items()}
        return [fix(v) for v in s] if isinstance(s, list) else s

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        if t.startswith("[") and t.endswith("]"):
            inner = named(t[1:-1])
            return None if inner is None else {"type": "array", "items": inner}
        return {"$ref": t} if t in types else None

    schema = named(type)
    if schema is None:
        return Validation(ok=False, errors=[f"тип {type} не найден"])
    checker = jsonschema.Draft202012Validator({**fix(schema), "$defs": fix(types)})
    found = sorted(checker.iter_errors(value), key=lambda e: ("/".join(map(str, e.path)), e.message))
    errors = [f"{'/'.join(map(str, e.path)) or '·'}: {e.message[:200]}" for e in found]
    return Validation(ok=not errors, errors=errors)


def size(type: str, env: TypeEnv) -> int:
    """Число узлов схемы: объект, список и скаляр — по узлу; ссылки раскрываются,
    повтор типа на том же пути (рекурсия) — один узел."""
    types = env.types

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        if t.startswith("[") and t.endswith("]"):
            return {"type": "array", "items": named(t[1:-1])}
        return {"$ref": t}

    def count(s, seen):
        if not isinstance(s, dict):
            return 1
        if "$ref" in s:
            ref = s["$ref"]
            return 1 if ref in seen or ref not in types else count(types[ref], seen | {ref})
        kids = list((s.get("properties") or {}).values())
        kids += [s[k] for k in ("items", "additionalProperties") if isinstance(s.get(k), dict)]
        kids += [x for k in ("oneOf", "anyOf", "allOf") for x in s.get(k) or []]
        return 1 + sum(count(k, seen) for k in kids)

    return count(named(type), frozenset())
