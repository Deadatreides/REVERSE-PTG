"""Контрольные случаи общего кода исполнения: обёртки условий (rptg._contract) и перевод
JSON ↔ dataclasses (rptg._values).

Обёртка обязана остановиться на первом нарушении и назвать сторону: requires — виновата
вызывающая схема, ensures — сама операция (LOGIC §5, Э6). Ошибка вычисления условия — нарушение,
а не сбой обёртки. Перевод значений проверяется туда и обратно на всех примерах карты: если хоть
один пример меняется при переводе, тесты примеров сравнивали бы не то.

    python -m pytest tests/test_runtime_controls.py -q
"""
import importlib
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

from rptg import _contract as c  # noqa: E402
from rptg._types import EvalResult, Example  # noqa: E402
from rptg._values import BadValue, dump, load  # noqa: E402

PRIMITIVE = {"string": str, "integer": int, "number": float, "boolean": bool}


def test_all_conditions_true_pass():
    c.check("app:f", "requires", [("x > 0", lambda: True), ("y > 0", lambda: True)])


@pytest.mark.parametrize("conds, why", [
    ([("x > 0", lambda: False)], "ложно"),
    ([("x / y > 1", lambda: 1 / 0 > 1)], "ZeroDivisionError"),
    ([("len(x) > 0", lambda: 1)], "не логическое"),
])
def test_violation_names_side_and_condition(conds, why):
    with pytest.raises(c.ContractError) as e:
        c.check("app:f", "ensures", conds)
    assert (e.value.op, e.value.side, e.value.cond) == ("app:f", "ensures", conds[0][0])
    assert why in e.value.why


def test_first_violation_wins():
    with pytest.raises(c.ContractError) as e:
        c.check("app:f", "requires", [("a", lambda: True), ("b", lambda: False), ("c", lambda: False)])
    assert e.value.cond == "b"


def test_generated_wrapper_blames_the_operation_for_its_output(monkeypatch):
    leaves = importlib.import_module("rptg.lang.cl.logic._leaves")
    decode = importlib.import_module("rptg.lang.cl.logic.decode")
    from rptg._types import Limits, Proof
    from rptg.lang.cl.logic._types import SmtText, SolveResult
    monkeypatch.setattr(decode, "proof", lambda answer, smt, limits: Proof(verdict="refuted", bound=limits.k_lists))
    limits = Limits(max_depth=8, max_children=7, final_max_ops=6, final_max_lines=40, max_complexity=10,
                    k_lists=3, z3_rlimit=1, hypothesis_examples=1)
    smt = SmtText(ok=True, errors=[], text="", kinds={}, goal_symbols=[], bound=3)
    with pytest.raises(c.ContractError) as e:
        leaves.decode.proof(answer=SolveResult(status="sat", model={}, core=[]), smt=smt, limits=limits)
    assert e.value.op == "rptg.lang.cl.logic.decode:proof" and e.value.side == "ensures"
    assert "counterexample != null" in e.value.cond


@pytest.mark.parametrize("tp, value, why", [
    (int, True, "ожидалось int"),
    (EvalResult, {"value": True}, "нет обязательного поля ok"),
    (EvalResult, {"ok": True, "value": True, "extra": 1}, "нет полей extra"),
    (list[int], {"a": 1}, "ожидался список"),
])
def test_load_rejects_wrong_values(tp, value, why):
    with pytest.raises(BadValue) as e:
        load(tp, value)
    assert why in str(e.value)


def test_keyword_field_keeps_its_json_name():
    obj = load(Example, {"in": {"x": 1}, "out": 2, "source": "user"})
    assert obj.in_ == {"x": 1}
    assert dump(obj) == {"in": {"x": 1}, "out": 2, "source": "user"}


def test_absent_optional_field_stays_absent():
    assert dump(EvalResult(ok=True, value=False)) == {"ok": True, "value": False}


def load_map():
    root = design_io.load(ROOT / "design" / "rptg.yaml")
    designs = [d for _, d in design_io.designs()]
    cards = [root["card"]] + [c for d in designs for c in d["children"]]
    owner = {n: "rptg" for n in yaml.safe_load((ROOT / "design" / "types.yaml").read_text(encoding="utf-8"))}
    owner.update({t["name"]: t["owner"] for d in designs for t in d.get("types") or []})
    return cards, owner


CARDS, OWNER = load_map()


def pytype(t):
    if t in PRIMITIVE:
        return PRIMITIVE[t]
    if t.startswith("[") and t.endswith("]"):
        return list[pytype(t[1:-1])]
    return getattr(importlib.import_module(OWNER[t] + "._types"), t)


def values():
    for card in CARDS:
        for op in card["ops"]:
            for i, ex in enumerate(op["examples"]):
                for p in op["params"]:
                    yield pytest.param(p["type"], ex["in"][p["name"]], id=f"{card['id']}:{op['name']}#{i}:{p['name']}")
                if ex.get("match") != "subset":
                    yield pytest.param(op["result"], ex["out"], id=f"{card['id']}:{op['name']}#{i}:out")


@pytest.mark.parametrize("type_name, value", list(values()))
def test_every_example_value_survives_the_round_trip(type_name, value):
    assert dump(load(pytype(type_name), value)) == value
