"""Контрольные случаи rptg.build: собранная программа запускается, отчёт читает check (LOGIC §5, Э1–Э3, Э6).

Каждый случай: rptg.build.files → файлы на диск → python run_tests.py в подпроцессе → report.json →
событие sandbox_finished → check.evaluate. Так проверяется весь договор сборки с проверкой, а не
текст модулей: верная функция проходит Э1–Э3, ошибка в коде даёт Э2/Э3 fail с нарушением и входом,
ошибка типов — Э1 fail на строке кода модели, дыра в схеме узла — Э6 fail с виновным, сбой оснастки —
unknown (ERROR ≠ FAIL), сбой кода модели при загрузке — провал примера (стадии отказа, эксп. 11/12).

    python -m pytest tests/test_build_controls.py -q
"""
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

pytest.importorskip("hypothesis")
pytest.importorskip("mypy")
needs_z3 = pytest.mark.skipif(importlib.util.find_spec("z3") is None, reason="check.evaluate доходит до решателя")

from rptg import _types as T  # noqa: E402
from rptg._values import dump, load  # noqa: E402

import rptg.build as build  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.build.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["fixtures"]}
CFG = load(T.Config, FX["cfg"])


def files(state, target):
    return build.files(state=load(T.State, state), target=load(T.BuildTarget, target), cfg=CFG).files


def run(state, target, tmp, what="all", drop=()):
    """Собрать, записать, прогнать; событие sandbox_finished для check."""
    for path, text in files(state, target).items():
        if path in drop:
            continue
        (tmp / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp / path).write_text(text, encoding="utf-8")
    proc = subprocess.run([sys.executable, "run_tests.py", what], cwd=tmp, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    report = json.loads((tmp / "report.json").read_text(encoding="utf-8")) if (tmp / "report.json").exists() else None
    return {"kind": "sandbox_finished", "target": target,
            "output": {"exit_code": proc.returncode, "timed_out": False, "report": report, "stderr_tail": proc.stderr[-2000:]}}


def verdicts(state, event):
    import rptg.check as check
    evidence = check.evaluate(state=load(T.State, state), event=load(T.Event, event), cfg=CFG)
    return {e.check: dump(e) for e in evidence}


def with_code(key, code):
    s = copy.deepcopy(FX["s_build"])
    s["code"][key] = code
    return s


LT = "app.billing.lines:line_total"
T_FN = {"kind": "function_tests", "subject": LT}
T_PKG = {"kind": "node_package", "subject": "app.billing"}
T_PROG = {"kind": "program", "subject": "app"}


# ── функция: Э1 mypy, Э2 примеры, Э3 свойства ──

@needs_z3
def test_correct_function_passes_e1_e2_e3(tmp_path):
    event = run(FX["s_build"], T_FN, tmp_path)
    assert event["output"]["exit_code"] == 0, event["output"]["stderr_tail"]
    got = verdicts(FX["s_build"], event)
    assert got["E1"]["verdict"] == "pass" and got["E1"]["tool"] == "mypy"
    assert got["E2"]["verdict"] == "pass" and got["E2"]["subject"] == "function:" + LT
    assert got["E3"]["verdict"] == "pass"
    props = event["output"]["report"]["properties"]
    # границы qty > 0, price >= 0 порождаются, а не фильтруются: годных входов — сколько просили
    assert props[0]["examples"] == CFG.limits.hypothesis_examples and not props[0].get("too_few")


@needs_z3
def test_wrong_function_fails_e2_and_e3_with_violation(tmp_path):
    bad = "def line_total(line: InvoiceLine) -> Money:\n    return Money(amount=line.qty + line.price, currency=line.currency)\n"
    state = with_code(LT, bad)
    got = verdicts(state, run(state, T_FN, tmp_path))
    assert got["E2"]["verdict"] == "fail"
    assert got["E2"]["details"]["violation"]["side"] == "ensures"
    assert got["E2"]["details"]["violation"]["op"] == LT
    assert got["E3"]["verdict"] == "fail" and got["E3"]["counterexample"]["line"]["qty"] > 0


SPOILER = ("def line_total(line: InvoiceLine) -> Money:\n"
           "    line.price, line.qty = line.price * line.qty, 1\n"
           "    return Money(amount=line.price, currency=line.currency)\n")


@needs_z3
def test_function_that_changes_its_input_fails_e2_and_e3_on_purity(tmp_path):
    """Чистота (LOGIC §5, Э2): «нормализация на месте» — результат верен и гарантии на изменённом
    входе выполняются (1·20 = 20), но вход стал другим. Ловит только сверка входа до и после вызова;
    в отчёт для починки идёт, какой параметр трогать нельзя."""
    state = with_code(LT, SPOILER)
    event = run(state, T_FN, tmp_path, what="tests")
    row, prop = event["output"]["report"]["examples"][0], event["output"]["report"]["properties"][0]
    assert row["actual"] == {"amount": "20.00", "currency": "EUR"}                # значение верное
    assert not row["ok"] and row["violation"]["side"] == "purity"
    assert not prop["ok"] and prop["violation"]["side"] == "purity"
    got = verdicts(state, event)
    assert got["E2"]["verdict"] == "fail" and got["E3"]["verdict"] == "fail"
    assert got["E2"]["details"]["violation"] == {"op": LT, "side": "purity", "cond": "параметры не меняются: line",
                                                 "why": "вызов изменил свой вход"}
    assert got["E2"]["details"]["expected"] == "параметры не меняются: line"


@needs_z3
def test_type_error_fails_e1_on_model_line(tmp_path):
    bad = "def line_total(line: InvoiceLine) -> Money:\n    total: int = line.price\n    return Money(amount=line.qty * line.price, currency=line.currency)\n"
    state = with_code(LT, bad)
    got = verdicts(state, run(state, T_FN, tmp_path, what="mypy"))
    assert got["E1"]["verdict"] == "fail" and got["E1"]["tool"] == "mypy"
    assert got["E1"]["details"]["problems"][0].startswith("строка 2:")        # строка кода модели, не файла
    assert "E2" not in got                                                    # тесты не гонялись


@needs_z3
def test_model_code_with_future_import_builds_and_keeps_line_numbers(tmp_path):
    """from __future__ в коде модели поднимается в заголовок модуля, а его строка в коде гаснет:
    иначе модуль не грузится (импорт __future__ после других), а строки mypy съезжают."""
    code = ("from __future__ import annotations\n\n\ndef line_total(line: InvoiceLine) -> Money:\n"
            "    return Money(amount=line.qty * line.price, currency=line.currency)\n")
    state = with_code(LT, code)
    got = verdicts(state, run(state, T_FN, tmp_path))
    assert got["E1"]["verdict"] == "pass" and got["E2"]["verdict"] == "pass"
    bad = "from __future__ import annotations\n" + code.split("\n", 1)[1].replace(
        "    return", "    total: int = line.price\n    return")
    state = with_code(LT, bad)
    got = verdicts(state, run(state, T_FN, tmp_path / "bad", what="mypy"))
    assert got["E1"]["details"]["problems"][0].startswith("строка 5:")       # строка модели, не файла


@needs_z3
def test_model_import_failure_is_a_failed_example_not_harness_error(tmp_path):
    bad = "def line_total(line: InvoiceLine, k: int = UNDEFINED) -> Money:\n    return Money(amount=line.qty * line.price, currency=line.currency)\n"
    state = with_code(LT, bad)
    event = run(state, T_FN, tmp_path, what="tests")
    assert event["output"]["exit_code"] == 0 and event["output"]["report"]["examples"][0]["error"].startswith("NameError")
    assert verdicts(state, event)["E2"]["verdict"] == "fail"


@needs_z3
def test_condition_that_raises_is_a_violation_of_its_side(tmp_path):
    """LOGIC §4.4: условие, упавшее при вычислении, — нарушение, а не сбой и не «истина»."""
    bad = "def line_total(line: InvoiceLine) -> Money:\n    return None  # type: ignore[return-value]\n"
    state = with_code(LT, bad)
    event = run(state, T_FN, tmp_path, what="tests")
    row = event["output"]["report"]["examples"][0]
    assert row["violation"]["side"] == "ensures" and row["violation"]["why"].startswith("AttributeError")
    assert verdicts(state, event)["E2"]["verdict"] == "fail"


@needs_z3
def test_decimal_result_is_compared_by_number_not_text(tmp_path):
    """LOGIC §5 Э2: 20 и 20.00 — одно число; другая запись итога — не провал примера."""
    code = ("def line_total(line: InvoiceLine) -> Money:\n"
            "    return Money(amount=(line.qty * line.price).normalize(), currency=line.currency)\n")
    state = with_code(LT, code)
    event = run(state, T_FN, tmp_path, what="tests")
    assert event["output"]["report"]["examples"][0]["actual"]["amount"] == "20"
    got = verdicts(state, event)
    assert got["E2"]["verdict"] == "pass" and got["E3"]["verdict"] == "pass"


@needs_z3
def test_too_few_valid_inputs_is_unknown_not_fail(tmp_path):
    """Требование, которое граница не выражает и фильтр почти не пропускает: свойство не набрало
    входов — это «не знаю» (Э3 unknown), а не провал функции."""
    state = copy.deepcopy(FX["s_build"])
    op = state["cards"]["app.billing.lines"]["ops"][0]
    op["requires"] = op["requires"] + ["line.qty % 1000 == 777"]
    op["examples"] = [{"in": {"line": {"qty": 777, "price": "1.00", "currency": "EUR"}},
                       "out": {"amount": "777.00", "currency": "EUR"}, "source": "model"}]
    event = run(state, T_FN, tmp_path, what="tests")
    assert event["output"]["report"]["properties"][0]["too_few"] is True
    got = verdicts(state, event)
    assert got["E2"]["verdict"] == "pass" and got["E3"]["verdict"] == "unknown"


@needs_z3
def test_harness_failure_gives_unknown_not_fail(tmp_path):
    event = run(FX["s_build"], T_FN, tmp_path, drop=("app/_rt.py",))
    assert event["output"]["exit_code"] == 2 and event["output"]["report"] is None
    got = verdicts(FX["s_build"], event)
    assert got["E2"]["verdict"] == "unknown" and got["E3"]["verdict"] == "unknown"


# ── сборка узла: Э6 с виновным ──

@needs_z3
def test_assembled_node_passes_e6_examples_and_properties(tmp_path):
    """Свойство сборки идёт, а не тонет в фильтре: len(order.lines) >= 1 и условия на элементах под
    forall — границы порождения (lang.cl_strategy), фильтру остаётся только равенство валют."""
    event = run(FX["s_build"], T_PKG, tmp_path, what="tests")
    assert event["output"]["exit_code"] == 0, event["output"]["stderr_tail"]
    rows, props = event["output"]["report"]["examples"], event["output"]["report"]["properties"]
    assert rows and all(r["ok"] for r in rows)
    assert [p["op"] for p in props] == ["make_invoice"] and props[0]["ok"] and not props[0].get("too_few")
    got = verdicts(FX["s_build"], event)["E6"]
    assert got["subject"] == "assembly:app.billing" and got["verdict"] == "pass"


@needs_z3
def test_currency_hole_is_found_by_the_property_alone(tmp_path):
    """Без подсказки примером: свойство сборки само порождает заказ с двумя валютами, нарушение
    requires у money:add — виновна схема узла."""
    state = copy.deepcopy(FX["s_build"])
    state["cards"]["app.billing"] = FX["c_billing"]              # карточка без «одна валюта у всех строк»
    event = run(state, T_PKG, tmp_path, what="tests")
    assert all(r["ok"] for r in event["output"]["report"]["examples"])          # примеры одной валюты
    prop = event["output"]["report"]["properties"][0]
    assert not prop["ok"] and prop["violation"]["op"] == "app.money:add"
    assert len({line["currency"] for line in prop["counterexample"]["order"]["lines"]}) == 2
    got = verdicts(state, event)["E6"]
    assert got["verdict"] == "fail" and got["details"]["blame"] == "design:app.billing"


@needs_z3
def test_currency_hole_is_blamed_on_the_node_design(tmp_path):
    """LOGIC §9: схема app.billing складывает суммы разных валют — требование money:add на входе
    нарушено, виновна схема узла (таблица вины Э6)."""
    state = copy.deepcopy(FX["s_build"])
    state["cards"]["app.billing"] = FX["c_billing"]              # карточка без «одна валюта у всех строк»
    mixed = {"in": {"order": {"id": 9, "lines": [{"qty": 1, "price": "1.00", "currency": "EUR"},
                                                 {"qty": 1, "price": "2.00", "currency": "USD"}]}},
             "out": {"order_id": 9, "total": {"amount": "3.00", "currency": "EUR"}}, "source": "user"}
    state["user_examples"]["app.billing:make_invoice"] = [mixed]
    got = verdicts(state, run(state, T_PKG, tmp_path, what="tests"))
    assert got["E6"]["verdict"] == "fail"
    assert got["E6"]["details"]["violation"]["op"] == "app.money:add"
    assert got["E6"]["details"]["violation"]["side"] == "requires"
    assert got["E6"]["details"]["blame"] == "design:app.billing"


@needs_z3
def test_assembly_that_changes_its_input_fails_e6_on_purity(tmp_path):
    """Лист в сборке правит строки заказа на месте: итог верен, условия чисты, но make_invoice
    изменил свой вход — Э6 fail стороны purity на границе узла. Трасса виновного не называет, поэтому
    вина по умолчанию — разложение узла; сам лист ловят его Э2 и Э3 раньше сборки."""
    state = with_code(LT, SPOILER)
    event = run(state, T_PKG, tmp_path, what="tests")
    got = verdicts(state, event)["E6"]
    assert got["verdict"] == "fail"
    assert got["details"]["violation"]["op"] == "app.billing:make_invoice" and got["details"]["violation"]["side"] == "purity"
    assert got["details"]["blame"] == "design:app.billing"


# ── программа целиком ──

@needs_z3
def test_program_runs_user_examples(tmp_path):
    event = run(FX["s_build"], T_PROG, tmp_path, what="tests")
    assert event["output"]["exit_code"] == 0, event["output"]["stderr_tail"]
    rows, props = event["output"]["report"]["examples"], event["output"]["report"]["properties"]
    assert [r["ok"] for r in rows] == [True, True]                    # два примера пользователя app:invoice
    assert props[0]["ok"] and not props[0].get("too_few")
    assert verdicts(FX["s_build"], event)["E6"]["verdict"] == "pass"


def test_program_layout_matches_logic():
    got = files(FX["s_build"], T_PROG)
    for path in ["app/__init__.py", "app/_flows.py", "app/_types.py", "app/_rt.py", "app/money.py",
                 "app/billing/__init__.py", "app/billing/_flows.py", "app/billing/lines.py", "tests/test_app.py", "run_tests.py"]:
        assert path in got, path
    assert "app/types.py" not in got                                      # С-14: модуль типов — _types.py
