"""Язык условий на всём корпусе карты rptg — не только на примерах своих карточек.

1. Каждое условие каждой операции карты проходит разбор и проверку типов (П1): окружение —
   параметры операции, в ensures ещё и result.
2. Два исполнения условия согласны: вычисление обходом дерева (evaluate, данные — JSON) и перевод
   в Python (python, данные — объекты dataclasses) дают одно значение на каждом точном примере
   каждой операции. Расхождение значит, что ошибся один из двух листов.

    python -m pytest tests/test_cl_corpus.py -q
"""
import importlib
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

from rptg._values import load  # noqa: E402
from rptg.lang.cl.evaluate import evaluate  # noqa: E402
from rptg.lang.cl.parse import parse  # noqa: E402
from rptg.lang.cl.python import python  # noqa: E402
from rptg.lang.cl.typecheck import typecheck  # noqa: E402
from rptg.lang.types import env as type_env  # noqa: E402
from rptg._types import Param, TypeDef  # noqa: E402

PRIMITIVE = {"string": str, "integer": int, "number": float, "boolean": bool}


def load_map():
    root = design_io.load(ROOT / "design" / "rptg.yaml")
    designs = [d for _, d in design_io.designs()]
    cards = [("rptg", root["card"])] + [(c["id"], c) for d in designs for c in d["children"]]
    raw = yaml.safe_load((ROOT / "design" / "types.yaml").read_text(encoding="utf-8"))
    typedefs = [TypeDef(name=n, owner="rptg", doc=b.get("doc"), schema=b["schema"]) for n, b in raw.items()]
    typedefs += [TypeDef(name=t["name"], owner=t["owner"], doc=t.get("doc"), schema=t["schema"])
                 for d in designs for t in d.get("types") or []]
    return cards, typedefs


CARDS, TYPEDEFS = load_map()
OWNER = {t.name: t.owner for t in TYPEDEFS}


def pytype(t):
    if t in PRIMITIVE:
        return PRIMITIVE[t]
    if t.startswith("[") and t.endswith("]"):
        return list[pytype(t[1:-1])]
    return getattr(importlib.import_module(OWNER[t] + "._types"), t)


def typed_conditions(op, side):
    params = [Param(name=p["name"], type=p["type"]) for p in op["params"]]
    if side == "ensures":
        params.append(Param(name="result", type=op["result"]))
    made = type_env(TYPEDEFS, params)
    assert made.ok, made.errors
    return [(text, typecheck(parse(text), made.env)) for text in op[side]]


def conditions():
    for node_id, card in CARDS:
        for op in card["ops"]:
            for side in ("requires", "ensures"):
                for i, text in enumerate(op[side]):
                    yield pytest.param(node_id, op, side, i, id=f"{node_id}:{op['name']}:{side}#{i}")


@pytest.mark.parametrize("node_id, op, side, i", list(conditions()))
def test_condition_typechecks(node_id, op, side, i):
    text, typed = typed_conditions(op, side)[i]
    assert typed.ok, f"«{text}»: {typed.errors}"


def examples():
    for node_id, card in CARDS:
        for op in card["ops"]:
            for i, ex in enumerate(op["examples"]):
                if ex.get("match") != "subset" and (op["requires"] or op["ensures"]):
                    yield pytest.param(node_id, op, ex, id=f"{node_id}:{op['name']}#{i}")


def run_python(expr, scope):
    """Выражение обёртки в тех же условиях, что в сгенерированном модуле: Decimal и значения-объекты.
    Имена — глобальными: генератор внутри eval не видит отдельного словаря локальных имён."""
    try:
        return {"ok": True, "value": eval(expr, {"Decimal": Decimal, **scope})}  # тест, не лист: eval здесь законен
    except ZeroDivisionError:
        return {"ok": True, "value": False}
    except Exception as e:  # ошибка вычисления — как у evaluate: условие не вычислилось
        return {"ok": False, "error": repr(e)}


@pytest.mark.parametrize("node_id, op, example", list(examples()))
def test_two_executions_agree(node_id, op, example):
    data = dict(example["in"])
    objects = {p["name"]: load(pytype(p["type"]), data[p["name"]]) for p in op["params"]}
    sides = [("requires", data, objects)]
    if "out" in example:
        sides.append(("ensures", {**data, "result": example["out"]},
                      {**objects, "result": load(pytype(op["result"]), example["out"])}))
    for side, json_values, object_values in sides:
        for text, typed in typed_conditions(op, side):
            if not typed.ok:
                continue  # такое условие уже упало в test_condition_typechecks
            walked = evaluate(typed, json_values)
            compiled = run_python(python(typed), object_values)
            if walked.ok and compiled["ok"]:
                assert walked.value == compiled["value"], f"{side} «{text}»: evaluate {walked.value}, python {compiled['value']}"
            else:
                assert walked.ok == compiled["ok"], f"{side} «{text}»: evaluate {walked}, python {compiled}"
