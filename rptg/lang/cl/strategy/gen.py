"""Лист rptg.lang.cl.strategy.gen — стратегия Hypothesis по типу параметра и его границам.

Функции приняты по карточке design/rptg.lang.cl.strategy.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Params, StrMap, TypeEnv
    from rptg.lang.cl.strategy._types import Bounds


def gen(params: Params, bounds: Bounds, env: TypeEnv) -> StrMap:
    """По стратегии на параметр; границы схемы тоже учитываются, из двух берётся более тесная.
    Граница ищется по пути места: поле — через точку, элемент списка — [] (значения словаря путей
    не имеют). Стратегия порождает JSON по схеме (в объекты его переводит тест); рекурсия типа —
    st.nothing()."""
    types, found = env.types, {(b.name, b.what, b.side): b.v for b in bounds}

    def call(fn, **kw):
        return f"st.{fn}(" + ", ".join(f"{k}={v}" for k, v in kw.items() if v is not None) + ")"

    def number(t, s, name):
        lo, hi = found.get((name, "value", "min")), found.get((name, "value", "max"))
        lo = s.get("minimum") if lo is None else lo if s.get("minimum") is None else max(lo, s["minimum"])
        hi = s.get("maximum") if hi is None else hi if s.get("maximum") is None else min(hi, s["maximum"])
        if t == "integer":
            return call("integers", min_value=lo, max_value=hi)
        text = call("floats" if t == "number" else "decimals", min_value=lo, max_value=hi, allow_nan=False,
                    allow_infinity=False)
        return text if t == "number" else text + ".map(str)"

    def record(s, name, seen):
        required, parts = s.get("required", []), {True: [], False: []}
        for k, v in s["properties"].items():
            parts[k in required].append(f"{json.dumps(k, ensure_ascii=False)}: {strat(v, f'{name}.{k}', seen)}")
        return f"st.fixed_dictionaries({{{', '.join(parts[True])}}}, optional={{{', '.join(parts[False])}}})"

    def sized(t, s, name, seen):
        size = {"min_size": found.get((name, "size", "min")), "max_size": found.get((name, "size", "max"))}
        if t == "array":
            return call("lists", elements=strat(s.get("items", {}), name + "[]", seen), **size)
        return f"st.from_regex({json.dumps(s['pattern'])}, fullmatch=True)" if "pattern" in s else call("text", **size)

    def deref(s, seen):
        while "$ref" in s and s["$ref"] != "Decimal":
            if s["$ref"] in seen or s["$ref"] not in types:
                return None, seen
            seen, s = seen + (s["$ref"],), types[s["$ref"]]
        return s, seen

    def strat(s, name, seen):
        s, seen = deref(s, seen)
        if s is None:
            return "st.nothing()"
        t = "decimal" if "$ref" in s else s.get("type")
        if "enum" in s:
            return f"st.sampled_from({json.dumps(s['enum'], ensure_ascii=False)})"
        if t in ("integer", "number", "decimal"):
            return number(t, s, name)
        if t in ("string", "array"):
            return sized(t, s, name, seen)
        if t == "object":
            extra = strat(s.get("additionalProperties") or {}, name + "{}", seen)
            return record(s, name, seen) if "properties" in s else call("dictionaries", keys="st.text()", values=extra)
        return "st.booleans()" if t == "boolean" else "st.none() | st.booleans() | st.integers() | st.text()"

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        return {"type": "array", "items": named(t[1:-1])} if t.startswith("[") else {"$ref": t}

    return {p.name: strat(named(p.type), p.name, ()) for p in params}
