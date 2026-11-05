"""Примеры карточек — тесты на собранном коде (LOGIC §5, Э2 и Э6).

Каждая операция узла, у которого есть код, вызывается на входе каждого своего примера через обёртки
условий: нарушенное requires или ensures падает с ContractError и называет виновного. Вход примера
переводится из JSON в объекты сгенерированных типов, результат — обратно в JSON (rptg._values) и
сравнивается с out — точно (числа с плавающей точкой с допуском 1e-9) или по подмножеству.
Примеры, путь которых доходит до решателя, требуют z3; без него они пропускаются с причиной, а не
считаются пройденными.

    python -m pytest tests/test_cards.py -q
"""
import copy
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

HAS_Z3 = importlib.util.find_spec("z3") is not None
SOLVER = "rptg.lang.cl.logic.solve:run"
PRIMITIVE = {"string": str, "integer": int, "number": float, "boolean": bool}


def load_map():
    root = design_io.load(ROOT / "design" / "rptg.yaml")
    designs = {d["node"]: d for _, d in design_io.designs()}
    cards = {"rptg": root["card"]}
    for d in designs.values():
        for c in d["children"]:
            cards[c["id"]] = c
    owner = {n: "rptg" for n in yaml.safe_load((ROOT / "design" / "types.yaml").read_text(encoding="utf-8"))}
    for d in designs.values():
        owner.update({t["name"]: t["owner"] for t in d.get("types") or []})
    return cards, designs, owner


CARDS, DESIGNS, OWNER = load_map()


def pytype(t):
    """Тип Python по имени типа карточки: простой, [T] или сгенерированный."""
    if t in PRIMITIVE:
        return PRIMITIVE[t]
    if t.startswith("[") and t.endswith("]"):
        return list[pytype(t[1:-1])]
    return getattr(importlib.import_module(OWNER[t] + "._types"), t)


def calls(node_id, flow):
    """Полные имена операций, которые вызывает схема."""
    card = CARDS[node_id]
    kids = {c["id"].rsplit(".", 1)[1]: c for c in DESIGNS[node_id]["children"]}
    kids.update({u.rsplit(".", 1)[1]: CARDS[u] for u in card.get("uses", [])})
    out = set()
    for n in flow["nodes"]:
        ref = n.get("call") or n.get("map") or n.get("fold")
        if ref:
            short, _, op = ref.partition(":")
            target = kids[short]
            out.add(f"{target['id']}:{op or target['ops'][0]['name']}")
    return out


def reaches_solver(qual, seen=()):
    if qual == SOLVER:
        return True
    node_id, op = qual.split(":")
    if node_id not in DESIGNS or qual in seen:
        return False
    return any(reaches_solver(c, seen + (qual,)) for c in calls(node_id, DESIGNS[node_id]["flows"][op]))


def has_code(node_id):
    path = ROOT.joinpath(*node_id.split("."))
    return (path / "_flows.py").exists() if node_id in DESIGNS else path.with_suffix(".py").exists()


def operation(node_id, op):
    if node_id in DESIGNS:
        return getattr(importlib.import_module(node_id), op)
    parent, short = node_id.rsplit(".", 1)
    return getattr(getattr(importlib.import_module(parent + "._leaves"), short), op)


def cases():
    """Примеры каждой операции с кодом — и корня: с 04.10.2026 обвязку корня пишет скрипт, и примеры
    пользователя у девяти операций корня — приёмка всего ядра."""
    for node_id, card in CARDS.items():
        if not has_code(node_id):
            continue
        for op in card["ops"]:
            for i, ex in enumerate(op["examples"]):
                yield pytest.param(node_id, op, ex, id=f"{node_id}:{op['name']}#{i}")


def same(expected, actual, subset):
    """Точное равенство или подмножество: словарь — указанные ключи, список — та же длина, "*" — любое."""
    if subset and expected == "*":
        return True
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or (not subset and set(expected) != set(actual)):
            return False
        return all(k in actual and same(v, actual[k], subset) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and \
            all(same(e, a, subset) for e, a in zip(expected, actual))
    if isinstance(expected, float) or isinstance(actual, float):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and abs(expected - actual) <= 1e-9
    return type(expected) is type(actual) and expected == actual


@pytest.mark.parametrize("node_id, op, example", list(cases()))
def test_example(node_id, op, example):
    """Пример — результат и чистота: операция не меняет свой вход. Значения JSON в записях — те же
    объекты, что во входе примера, а якоря YAML делят их между примерами: изменённый на месте вход
    портит чужие примеры и делает исход зависимым от порядка (найдено на plan 01.10.2026)."""
    from rptg._values import dump, load
    if not HAS_Z3 and reaches_solver(f"{node_id}:{op['name']}"):
        pytest.skip("путь примера доходит до решателя, а z3-solver не установлен")
    before = copy.deepcopy(example["in"])
    args = {p["name"]: load(pytype(p["type"]), example["in"][p["name"]]) for p in op["params"]}
    actual = dump(operation(node_id, op["name"])(**args))
    changed = sorted(k for k in before if before[k] != example["in"][k])
    example["in"].update(before)
    assert not changed, f"операция изменила свой вход: {changed}"
    assert same(example["out"], actual, example.get("match") == "subset"), \
        f"ожидалось {example['out']!r}, получено {actual!r}"
