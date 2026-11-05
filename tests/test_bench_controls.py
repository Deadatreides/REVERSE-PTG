"""Контрольные случаи rptg.bench: калибровка от эталонного набора до назначения оператора (LOGIC §6.4).

Круг: bench.plan → задачи → итоги (записанные по правилу «кто какой род решает») → bench.table →
plan.assign. Таблицу, которую строит bench, читает маршрутизация plan — проверяется договор между ними
(К-4), а не только каждая сторона. Плюс свойства раздела (детерминизм, от порядка набора не зависит,
половины почти равны) и таблицы (равная выборка, выбор по подбору, цена с неудачами, порядок итогов
не важен, записи разного масштаба).

    python -m pytest tests/test_bench_controls.py -q
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

from rptg import _types as T  # noqa: E402
from rptg._values import dump, load  # noqa: E402

import rptg.bench as bench  # noqa: E402
import rptg.plan as plan  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.bench.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["fixtures"]}
CFG = load(T.Config, FX["cfg"])
OPERATORS = ["gguf", "mini", "gemini"]
PRICE = {"gguf": "0", "mini": "0.0020", "gemini": "0.0180"}


def reference(classes=("compute", "text", "search"), per_class=12):
    """Эталонный набор: per_class задач на род (LOGIC §6.4: по 12 на род), финальный узел с одной операцией."""
    card = FX["ref_double"]["card"]
    items = [{"id": f"{c}-{i:02d}", "class": c, "card": {**card, "id": f"ref.{c}{i:02d}"}, "hidden_tests": {}}
             for c in classes for i in range(1, per_class + 1)]
    return {"name": "контроль", "items": items}


def calibrate(ref, solves, operators=OPERATORS, cost=None):
    """План, итоги каждой задачи по правилу solves(оператор, задача) → passed, таблица."""
    cost = cost or (lambda op, item: PRICE[op])
    p = bench.plan(reference=load(T.ReferenceSet, ref), operators=operators, cfg=CFG)
    by_card = {f"function:{i['card']['id']}:double": i for i in ref["items"]}
    results = [{"item": by_card[t.subject]["id"], "class": by_card[t.subject]["class"], "operator": t.operator,
                "passed": solves(t.operator, by_card[t.subject]), "cost": cost(t.operator, by_card[t.subject]), "finish_reason": "stop"}
               for t in p.tasks]
    table = bench.table(results=load(T.CalibrationResults, results), plan=p, cfg=CFG)
    return dump(p), results, table


def candidate(work):
    return load(T.Candidate, {"subject": f"function:app.x:{work}", "kind": "function", "role": "implementer", "class": work,
                              "prior": 20, "level": 3})


def chosen(work, table):
    a = plan.assign(candidate=candidate(work), table=table, cfg=CFG)
    return a.operator, a.decided_by


SPECIALISTS = {"compute": "gguf", "text": "mini"}


def specialists(op, item):
    """gguf решает compute, mini — text, gemini — всё, включая search."""
    return op == "gemini" or SPECIALISTS.get(item["class"]) == op


# ── раздел и равная выборка ──

def test_every_operator_gets_every_task():
    """Сравнение — только при равной выборке (LOGIC §6.4): у каждого оператора одни и те же задачи."""
    p, _, _ = calibrate(reference(), specialists)
    by_op = {op: sorted(t["subject"] for t in p["tasks"] if t["operator"] == op) for op in OPERATORS}
    assert len(p["tasks"]) == 36 * 3
    assert by_op["gguf"] == by_op["mini"] == by_op["gemini"] and len(set(by_op["gguf"])) == 36


def test_split_is_fixed_and_independent_of_the_set_order():
    """Раздел фиксирован до прогона: тот же набор в другом порядке даёт те же половины."""
    ref = reference()
    a, _, _ = calibrate(ref, specialists)
    flipped = {**ref, "items": list(reversed(ref["items"]))}
    b, _, _ = calibrate(flipped, specialists)
    assert (a["fit"], a["check"]) == (b["fit"], b["check"])
    assert set(a["fit"]).isdisjoint(a["check"]) and len(a["fit"]) + len(a["check"]) == 36
    assert len(a["fit"]) - len(a["check"]) in (0, 1)


def test_split_divides_every_class_evenly():
    """К-8 (утверждено 02.10.2026): порядок «род, затем хэш» — каждый род делится поровну. Общий порядок по
    хэшу на этом же наборе давал подбор/проверку 3/9, 8/4, 7/5 — победитель compute выбирался по трём задачам."""
    p, _, _ = calibrate(reference(), specialists)
    for work in ("compute", "text", "search"):
        assert (sum(i.startswith(work) for i in p["fit"]), sum(i.startswith(work) for i in p["check"])) == (6, 6)


# ── таблица → маршрутизация plan ──

def test_different_winners_route_each_class_to_its_specialist():
    """G0: у родов разные победители — маршрут по роду; самый дешёвый годный на успех (LOGIC §6.4)."""
    _, _, table = calibrate(reference(), specialists)
    assert table.g0
    assert chosen("compute", table) == ("gguf", "table")
    assert chosen("text", table) == ("mini", "table")
    assert chosen("search", table) == ("gemini", "table")


def test_one_winner_everywhere_routes_by_the_pooled_rate():
    """Победитель один — G0 выключен, клетки оператора складываются по родам (К-4: вся выборка, все успехи)."""
    _, _, table = calibrate(reference(), lambda op, item: op == "gemini")
    assert not table.g0
    assert chosen("compute", table) == ("gemini", "table") and chosen("text", table) == ("gemini", "table")


def test_winner_is_chosen_on_the_fit_half_only():
    """К-1: в compute на подборе лучше gguf (всё против половины), а по всей выборке — mini (проверку
    решает только он). По всей выборке mini победил бы и compute, и text — G0 был бы ложью; по подбору
    победители разные — G0 включён."""
    ref = reference(classes=("compute", "text"))
    p, _, _ = calibrate(ref, specialists)
    fit = set(p["fit"])

    def swapped(op, item):
        if item["class"] == "text":
            return op == "mini"
        if item["id"] in fit:
            return op == "gguf" or int(item["id"][-2:]) % 2 == 0
        return op == "mini"

    _, _, table = calibrate(ref, swapped, operators=["gguf", "mini"])
    gguf, mini = ({k: getattr(c, k) for k in ("n_fit", "ok_fit", "ok_check")} for c in table.cells[:2])
    assert mini["ok_fit"] + mini["ok_check"] > gguf["ok_fit"] + gguf["ok_check"]      # по всей выборке — mini
    assert gguf["ok_fit"] > mini["ok_fit"]                                            # на подборе — gguf
    assert table.g0


def test_cost_per_success_counts_the_failed_attempts():
    """Цена на успех — все расходы клетки на успехи (arch2 c = total_cost / solved): mini решает половину
    задач text по 0,0020 за попытку — 0,0040 на успех."""
    ref = reference(classes=("text",), per_class=12)
    _, _, table = calibrate(ref, lambda op, item: op == "mini" and int(item["id"][-2:]) % 2 == 0, operators=["mini"])
    cell = table.cells[0]
    assert (cell.ok_fit + cell.ok_check, cell.n_fit + cell.n_check) == (6, 12)
    assert cell.cost_per_success == "0.0040"


def test_no_success_costs_all_attempts_and_never_routes():
    """К-2: успехов нет — цена всех попыток, доля 0, в маршрут клетка не попадает."""
    _, _, table = calibrate(reference(classes=("search",)), lambda op, item: op != "mini", operators=["mini", "gemini"])
    cells = {c.operator: c for c in table.cells}
    assert cells["mini"].cost_per_success == "0.0240" and cells["mini"].ok_fit + cells["mini"].ok_check == 0
    assert chosen("search", table) == ("gemini", "table")


def test_table_does_not_depend_on_the_order_of_results():
    ref = reference()
    p, results, table = calibrate(ref, specialists)
    again = bench.table(results=load(T.CalibrationResults, list(reversed(results))), plan=load(T.CalibrationPlan, p), cfg=CFG)
    assert dump(again) == dump(table)


def test_rerun_replaces_the_earlier_result():
    """К-7: повтор пары (задача, оператор) — последний; иначе выборка перестала бы быть равной."""
    ref = reference(classes=("compute",), per_class=10)
    p, results, table = calibrate(ref, specialists, operators=["gguf"])
    first = copy.deepcopy(results[0])
    rerun = [{**first, "passed": False, "cost": "0.5"}] + results
    again = bench.table(results=load(T.CalibrationResults, rerun), plan=load(T.CalibrationPlan, p), cfg=CFG)
    assert dump(again) == dump(table)
    assert again.cells[0].n_fit + again.cells[0].n_check == 10


def test_prices_written_with_different_scales_compare_by_number():
    """К-3: «0.002» (так пишет talk.cost) и «0.0020» — одно число. Цена клетки — в масштабе длинной записи;
    G0 сравнивает по числу: в compute цены равны — побеждает имя (gguf), в text mini дешевле (0,0025 <
    0,003) — G0 включён. Сравнение записей как строк дало бы mini в обоих родах."""
    ref = reference(classes=("compute", "text"), per_class=10)
    written = {("gguf", "compute"): "0.0020", ("mini", "compute"): "0.002", ("gguf", "text"): "0.003", ("mini", "text"): "0.0025"}
    _, _, table = calibrate(ref, lambda op, item: True, operators=["gguf", "mini"], cost=lambda op, item: written[(op, item["class"])])
    assert [c.cost_per_success for c in table.cells] == ["0.0020", "0.002", "0.003", "0.0025"]
    assert table.g0
