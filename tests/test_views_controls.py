"""Контрольные случаи rptg.views: представления через операцию show с настоящим check (ARCHITECTURE §7, §8).

Вид ответа — вид запроса (гарантия корня); граф собранной программы — весь зелёный, каждая карточка один
раз, рёбра между узлами; приёмку узла даёт check, а не лист; исходы сходятся с элементами.

    python -m pytest tests/test_views_controls.py -q
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

import rptg.views as views  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.views.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["fixtures"]}
CFG = load(T.Config, FX["cfg"])


def show(state, **query):
    return dump(views.show(state=load(T.State, state), query=load(T.ViewQuery, query), cfg=CFG))


def built():
    """Программа накладных собрана: все разложения, функции и сборки приняты."""
    s = copy.deepcopy(FX["s_build"])
    s["phase"] = "DONE"
    for subject in ["map:app", "design:app", "design:app.billing", "function:app.billing.lines:line_total", "function:app.money:add",
                    "assembly:app.billing", "assembly:app"]:
        s["elements"][subject] = {"subject": subject, "kind": subject.split(":")[0], "state": "accepted", "attempts": 1, "form_retries": 0,
                                  "reports": [], "answer_hashes": []}
    return s


def test_every_kind_answers_with_its_own_kind():
    for kind in ("status", "node", "graph", "competence"):
        assert show(FX["s_design"], kind=kind, subject="app")["kind"] == kind


def test_built_program_is_all_green_and_every_card_appears_once():
    graph = show(built(), kind="graph")["data"]
    ids = [n["id"] for n in graph["nodes"]]
    assert sorted(ids) == sorted(built()["cards"]) and len(ids) == len(set(ids))
    assert {n["status"] for n in graph["nodes"]} == {"accepted"}
    assert all(e["from"] in ids and e["to"] in ids for e in graph["edges"])
    kinds = {n["id"]: n["kind"] for n in graph["nodes"]}
    assert kinds == {"app": "composite", "app.billing": "composite", "app.billing.lines": "final", "app.money": "final"}


def test_accepted_design_without_assembly_is_still_in_work():
    """Принятое разложение — не собранный узел: без принятой сборки составной узел жёлтый."""
    s = built()
    s["elements"]["assembly:app"]["state"] = "planned"
    status = {n["id"]: n["status"] for n in show(s, kind="graph")["data"]["nodes"]}
    assert status["app"] == "working" and status["app.billing"] == "accepted"


def test_node_acceptance_comes_from_check():
    """Код функции есть, прогонов нет — check говорит «не принята» и называет недостающие слои."""
    s = built()
    s["elements"]["function:app.money:add"]["state"] = "checking"
    node = show(s, kind="node", subject="app.money")["data"]
    [el] = node["elements"]
    assert el["subject"] == "function:app.money:add" and el["accepted"] is False and el["missing"]
    assert node["card"]["id"] == "app.money"


def test_status_and_outcomes_agree_with_elements():
    s = copy.deepcopy(FX["v_s_costs"])
    status = show(s, kind="status")["data"]
    states = [e["state"] for e in s["elements"].values()]
    assert (status["accepted"], status["planned"], status["nodes"]) == (states.count("accepted"), states.count("planned"), len(s["cards"]))
    comp = show(s, kind="competence")["data"]
    assert "не для сравнения операторов" in comp["note"]
    assert sum(r["tasks"] for r in comp["rows"]) == sum(1 for e in s["elements"].values() if e.get("assignment"))
