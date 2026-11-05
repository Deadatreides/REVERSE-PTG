"""Контрольные случаи проверок rptg.check (LOGIC §5; норма arch1: три вида на каждую проверку).

Каждый случай гонится через rptg.check.run_case — тот же конвейер, что evaluate гонит на событии, —
и сравнивает вердикт своей проверки с известным: верный вход — pass, заведомо неверный — fail,
неприменимый — проверка молчит (unknown у run_case значит «доказательств этого слоя нет»).
Случаи написаны по правилам LOGIC, а не подогнаны под вывод проверок (SEAM_MODEL §5.3): провал
случая — дефект проверки. В конце summarize обязан признать доверенными все слои.

    python -m pytest tests/test_check_controls.py -q
"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

pytest.importorskip("z3")

from rptg import _types as T  # noqa: E402
from rptg._values import load  # noqa: E402

import rptg.check as check  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.check.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["fixtures"]}
CFG = load(T.Config, FX["cfg"])


def answered(task, text, finish="stop"):
    return {"kind": "model_answered", "task": task,
            "answer": {"text": text, "input_tokens": 100, "output_tokens": 50, "cache_read_tokens": 0,
                       "finish_reason": finish, "refusal": False}}


def design_text(design):
    return json.dumps({k: v for k, v in design.items() if k != "node"}, ensure_ascii=False)


def with_lines(**changes):
    """Разложение накладных с изменённой карточкой ребёнка lines."""
    d = copy.deepcopy(FX["d_billing"])
    d["children"][0].update(changes)
    return d


def with_flow(nodes):
    d = copy.deepcopy(FX["d_billing"])
    d["flows"]["make_invoice"]["nodes"] = nodes
    return d


def line_op(**changes):
    op = copy.deepcopy(FX["c_lines"]["ops"][0])
    op.update(changes)
    return op


BILLING = {"state": FX["s_billing"], "event": FX["e_billing"]}
FIXED = {"state": FX["s_build"], "event": FX["e_billing"]}
FUNCTION = {"state": FX["s_build"], "event": FX["e_fn"]}
RUNS = {"state": FX["s_build"], "event": FX["e_runs"]}
TASK_B, TASK_F = FX["task_billing"], FX["task_gguf"]
MAP_ANSWER = json.dumps({"map_text": "# Карта app\n", "card": FX["c_app"],
                         "types": [FX["t_money"], FX["t_line"], FX["t_order"], FX["t_invoice"]]}, ensure_ascii=False)
N0, N1, N2 = (FX["d_billing"]["flows"]["make_invoice"]["nodes"][i] for i in range(3))


def design_case(state, design):
    return {"state": state, "event": answered(TASK_B, design_text(design))}


def function_case(code, text=None):
    return {"state": FX["s_build"], "event": answered(TASK_F, text if text is not None else f"```python\n{code}```\n")}


def sandbox(kind, subject, report, timed_out=False):
    output = {"exit_code": 0 if report else 1, "timed_out": timed_out, "report": report}
    return {"state": FX["s_build"], "event": {"kind": "sandbox_finished", "target": {"kind": kind, "subject": subject}, "output": output}}


EXAMPLE_OK = {"op": "make_invoice", "index": 0, "ok": True}
CASES = [
    # ── П1: форма ──
    ("p1-billing", "P1", BILLING, "pass"),
    ("p1-no-json", "P1", {"state": FX["s_map"], "event": FX["e_form"]}, "fail"),
    ("p1-truncated", "P1", {"state": FX["s_billing"], "event": answered(TASK_B, '{"children": [', "length")}, "fail"),
    ("p1-no-flows", "P1", design_case(FX["s_billing"], {k: v for k, v in FX["d_billing"].items() if k != "flows"}), "fail"),
    ("p1-extra-key", "P1", design_case(FX["s_billing"], {**FX["d_billing"], "comment": "лишний ключ"}), "fail"),
    ("p1-bad-condition", "P1", design_case(FX["s_billing"], with_lines(ops=[line_op(requires=["line.qty >"])])), "fail"),
    ("p1-not-boolean", "P1", design_case(FX["s_billing"], with_lines(ops=[line_op(requires=["line.qty + 1"])])), "fail"),
    ("p1-keyword-param", "P1", design_case(FX["s_billing"], with_lines(ops=[line_op(params=[{"name": "class", "type": "InvoiceLine"}])])), "fail"),
    ("p1-unseen-type", "P1", design_case(FX["s_billing"], with_lines(ops=[line_op(result="Price")])), "fail"),
    ("p1-unknown-callee", "P1", design_case(FX["s_billing"], with_flow([{"id": "n1", "call": "nosuch:op", "args": {}}])), "fail"),
    ("p1-sandbox", "P1", RUNS, "unknown"),
    # извлечение не строже договора (сверка с базой 29.09: мицелий _strip_think, LB2 ВДП v1, arch1 этап 8)
    ("p1-json-upper", "P1", {"state": FX["s_billing"], "event": answered(TASK_B, "```JSON\n" + design_text(FX["d_billing"]) + "\n```")}, "pass"),
    ("p1-plain-fence", "P1", {"state": FX["s_billing"], "event": answered(TASK_B, "```\n" + design_text(FX["d_billing"]) + "\n```")}, "pass"),
    ("p1-think-closed", "P1", {"state": FX["s_billing"], "event": answered(
        TASK_B, "<think>черновик:\n```json\n{}\n```\n</think>\n" + design_text(FX["d_billing"]))}, "pass"),
    ("p1-two-blocks", "P1", {"state": FX["s_billing"], "event": answered(
        TASK_B, "```json\n" + design_text(FX["d_billing"]) + "\n```\nили\n```json\n" + design_text(FX["d_billing"]) + "\n```")}, "fail"),
    ("p1-think-cut", "P1", {"state": FX["s_billing"], "event": answered(TASK_B, "<think>сначала перечислю детей", "length")}, "fail"),
    # ── П2: структура ──
    ("p2-billing", "P2", BILLING, "pass"),
    ("p2-dangling", "P2", design_case(FX["s_billing"], FX["d_billing_bad"]), "fail"),
    ("p2-big-child", "P2", design_case(FX["s_billing"], with_lines(est_lines=40)), "fail"),
    ("p2-foreign-uses", "P2", design_case(FX["s_billing"], with_lines(uses=["app.tax"])), "fail"),
    ("p2-function", "P2", FUNCTION, "unknown"),
    # ── П3: данные ──
    ("p3-billing", "P3", BILLING, "pass"),
    ("p3-edge-ok", "P3", {"source_type": "Money", "target_type": "Money", "env": FX["env_money"]}, "pass"),
    ("p3-edge-wrong", "P3", {"source_type": "string", "target_type": "integer", "env": FX["env_x"]}, "fail"),
    ("p3-field-type", "P3", design_case(FX["s_billing"], with_flow([N0, N1, N2, {"id": "n3", "record": "Invoice",
                                                                               "fields": {"order_id": "n0.currency", "total": "n2"}}])), "fail"),
    ("p3-map", "P3", {"state": FX["s_new"], "event": answered(FX["task_map"], MAP_ANSWER)}, "unknown"),
    # ── П4: условия ──
    ("p4-fixed", "P4", FIXED, "pass"),
    ("p4-currency", "P4", BILLING, "fail"),
    ("p4-contradiction", "P4", design_case(FX["s_build"], with_lines(ops=[line_op(requires=["line.qty > 0", "line.qty < 0"])])), "fail"),
    ("p4-function", "P4", FUNCTION, "unknown"),
    # ── П5: уточнение (считается, не блокирует) ──
    ("p5-billing", "P5", FIXED, "pass"),
    ("p5-negative-start", "P5", design_case(FX["s_build"], with_flow([{**N0, "fields": {"amount": {"const": "-1"}, "currency": "order.lines[0].currency"}},
                                                                      N1, N2, FX["d_billing"]["flows"]["make_invoice"]["nodes"][3]])), "fail"),
    ("p5-sandbox", "P5", RUNS, "unknown"),
    # ── П7: примеры ──
    ("p7-billing", "P7", BILLING, "pass"),
    ("p7-bad-example", "P7", design_case(FX["s_billing"], FX["ans_billing_badex"]["value"]), "fail"),
    ("p7-sandbox", "P7", RUNS, "unknown"),
    # ── Э1: статика ──
    ("e1-line-total", "E1", FUNCTION, "pass"),
    ("e1-import-os", "E1", function_case(FX["code_os"]), "fail"),
    ("e1-no-block", "E1", function_case("", "def line_total(line): return line"), "fail"),
    ("e1-eval", "E1", function_case("def line_total(line: InvoiceLine) -> Money:\n    return eval('line')\n"), "fail"),
    ("e1-python-upper", "E1", function_case("", "```Python\n" + FX["code_lt"] + "```\n"), "pass"),
    ("e1-python3", "E1", function_case("", "```python3\n" + FX["code_lt"] + "```\n"), "pass"),
    ("e1-qwen3-open-think", "E1", function_case("", "<think>\n\n```python\n" + FX["code_lt"] + "```\n"), "pass"),
    ("e1-think-draft", "E1", function_case("", "<think>\n```python\ndef x(): pass\n```\n</think>\n```python\n" + FX["code_lt"] + "```\n"), "pass"),
    ("e1-two-blocks", "E1", function_case("", "```python\n" + FX["code_lt"] + "```\nили\n```python\n" + FX["code_lt"] + "```\n"), "fail"),
    ("e1-design", "E1", BILLING, "unknown"),
    # ── Э2, Э3: прогон функции ──
    ("e2-ok", "E2", RUNS, "pass"),
    ("e2-bad", "E2", {"state": FX["s_build"], "event": FX["e_runs_bad"]}, "fail"),
    ("e2-design", "E2", BILLING, "unknown"),
    ("e3-ok", "E3", RUNS, "pass"),
    ("e3-bad", "E3", {"state": FX["s_build"], "event": FX["e_runs_bad"]}, "fail"),
    ("e3-timeout", "E3", sandbox("function_tests", "app.money:add", None, timed_out=True), "fail"),
    ("e3-design", "E3", BILLING, "unknown"),
    # ── Э6: сборка ──
    ("e6-ok", "E6", sandbox("node_package", "app.billing", {"examples": [EXAMPLE_OK], "properties": []}), "pass"),
    ("e6-bad", "E6", {"state": FX["s_build"], "event": {**FX["e_runs_bad"], "target": {"kind": "node_package", "subject": "app.billing"}}}, "fail"),
    ("e6-function", "E6", RUNS, "unknown"),
]


def run(case_id, check_name, given, expected):
    case = load(T.ControlCase, {"id": case_id, "check": check_name, "input": given, "expected": expected})
    return check.run_case(case, CFG)


@pytest.mark.parametrize("case_id, check_name, given, expected", CASES, ids=[c[0] for c in CASES])
def test_control_case(case_id, check_name, given, expected):
    result = run(case_id, check_name, given, expected)
    assert result.ok, f"{case_id}: ожидалось {expected}, получено {result.actual}"


def test_every_layer_has_all_three_kinds():
    kinds = {}
    for _, name, _, expected in CASES:
        kinds.setdefault(name, set()).add(expected)
    layers = ["P1", "P2", "P3", "P4", "P5", "P7", "E1", "E2", "E3", "E6"]
    assert sorted(kinds, key=layers.index) == layers
    assert all(kinds[name] == {"pass", "fail", "unknown"} for name in layers), kinds


def test_summary_trusts_every_layer():
    results = [run(*c) for c in CASES]
    report = check.summarize(results)
    assert [r.check for r in report.checks] == ["P1", "P2", "P3", "P4", "P5", "P7", "E1", "E2", "E3", "E6"]
    assert all(r.trusted for r in report.checks), [(r.check, r.failures) for r in report.checks if not r.trusted]


def test_failure_report_is_self_contained():
    """Отчёт о провале П4 на сквозном примере: место, фрагмент, ожидание и контрпример по путям заказа."""
    evidences = check.evaluate(load(T.State, FX["s_billing"]), load(T.Event, FX["e_billing"]), CFG)
    p4 = next(e for e in evidences if e.check == "P4")
    rep = check.report(p4, load(T.State, FX["s_billing"]))
    assert (rep.rule, rep.where, rep.expected) == ("I13", FX["r_currency"]["where"], "a.currency == b.currency")
    assert {"order.lines[0].currency", "order.lines[1].currency"} <= set(rep.counterexample)
    assert all(k.startswith(("order.", "len(order.")) for k in rep.counterexample)
