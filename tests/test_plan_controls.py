"""Контрольные случаи rptg.plan: круг plan_next → действие → событие → apply_event (LOGIC §6, §7).

Корневой обвязки ещё нет, поэтому plan_next и apply_event собраны здесь по схемам корня
(design/rptg.yaml: plan_next = candidates → assign → pick, apply_event = check.evaluate →
transition); ответы моделей — записанные тексты, прогоны — настоящая песочница (build.files и
run_tests.py в подпроцессе), проверка — настоящий check.

Гарантии исполнителя arch2 (SPEC §7.2) — в пошаговом исполнении: бюджет, доверие, PAR, STOP,
SWITCH, детерминизм, валидатор. Политика по умолчанию (§7.3): лестница, повтор формы, повтор по
хэшу. Повышение (§7.4), подозрение и ревизия владельца (§7.5), мёртвые операции (§7.6),
перепроверка устаревшего без модели (§7.7), остановки (§7.8), утверждение, команды, вина в Э6 и
сквозной круг программы накладных от замысла до DONE.

    python -m pytest tests/test_plan_controls.py -q
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
pytestmark = pytest.mark.skipif(importlib.util.find_spec("z3") is None, reason="check.evaluate доходит до решателя")

from rptg import _types as T  # noqa: E402
from rptg._values import dump, load  # noqa: E402

import rptg.build as build  # noqa: E402
import rptg.check as check  # noqa: E402
import rptg.lang as lang  # noqa: E402
import rptg.plan as plan  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.plan.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["fixtures"]}
TRUSTED = ["P1", "P2", "P3", "P4", "P5", "P7", "E1", "E2", "E3", "E6"]
TABLE = load(T.Competence, FX["table_empty"])
WHAT = {"e1_mypy": "mypy", "e2_e3": "tests", "e6": "tests", "smoke": "all"}


def config(**over):
    """cfg примеров с доверенными проверками: их вносит оболочка по итогу контрольных случаев check."""
    return load(T.Config, {**FX["cfg"], "trusted": TRUSTED, **over})


CFG = config()
UNTRUSTED = load(T.Config, FX["cfg"])


# ── оболочка: круг ядра ──

def plan_next(state, cfg=CFG):
    s = load(T.State, state)
    cands = plan.candidates(state=s, cfg=cfg)
    assigns = [plan.assign(candidate=c, table=TABLE, cfg=cfg) for c in cands]
    return dump(plan.pick(state=s, candidates=cands, assignments=assigns, cfg=cfg))


def apply_event(state, event, cfg=CFG):
    s, e = load(T.State, state), load(T.Event, event)
    return dump(plan.transition(state=s, event=e, evidence=check.evaluate(state=s, event=e, cfg=cfg), cfg=cfg))


def answered(task, text, tokens=(1000, 200)):
    return {"kind": "model_answered", "task": task,
            "answer": {"text": text, "input_tokens": tokens[0], "output_tokens": tokens[1], "cache_read_tokens": 0,
                       "finish_reason": "stop", "refusal": False}}


def user(**reply):
    return {"kind": "user_answered", "reply": reply}


def command(name, **more):
    return {"kind": "command", "reply": {"command": name, **more}}


def as_json(value):
    return "```json\n" + json.dumps(value, ensure_ascii=False) + "\n```\n"


def design_text(d):
    return as_json({k: v for k, v in d.items() if k != "node"})


def code_text(code):
    return "```python\n" + code + "```\n"


def sandbox(state, action, tmp, cfg=CFG):
    """Песочница оболочки: набор файлов во временную папку, run_tests.py, событие sandbox_finished."""
    target = action["target"]
    for path, text in build.files(state=load(T.State, state), target=load(T.BuildTarget, target), cfg=cfg).files.items():
        (tmp / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp / path).write_text(text, encoding="utf-8")
    proc = subprocess.run([sys.executable, "run_tests.py", WHAT[action["run"]]], cwd=tmp, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    report = json.loads((tmp / "report.json").read_text(encoding="utf-8")) if (tmp / "report.json").exists() else None
    (tmp / "report.json").unlink(missing_ok=True)
    return {"kind": "sandbox_finished", "target": target,
            "output": {"exit_code": proc.returncode, "timed_out": False, "report": report, "stderr_tail": proc.stderr[-2000:]}}


def drive(state, answer_for, tmp, cfg=CFG, steps=40, approve="yes"):
    """Круг оболочки до stop, паузы или вопроса, на который ответа нет; trail — (фаза, действие)."""
    trail = []
    for _ in range(steps):
        act = plan_next(state, cfg)
        trail.append((state["phase"], act))
        if act["kind"] == "call_model":
            event = answered(act["task"], answer_for(act["task"]))
        elif act["kind"] == "run_sandbox":
            event = sandbox(state, act, tmp, cfg)
        elif act["kind"] == "ask_user" and "approve" in act["question"] and approve:
            event = user(**act["question"], decision=approve)
        else:
            break
        state = apply_event(state, event, cfg)["state"]
    return state, trail


def element(state, subject):
    return state["elements"][subject]


def kinds(journal):
    return [(j["kind"], j["subject"]) for j in journal if j["kind"] not in ("evidence", "state")]


# ── политики на языке arch2 ──

def CALL(operator="assigned", wording="primary", report=False):
    return {"op": "CALL", "operator": operator, "wording": wording, "with_report": report}


CHECK = {"op": "CHECK"}


def SEQ(*kids):
    return {"op": "SEQ", "children": list(kids)}


def PAR(*kids):
    return {"op": "PAR", "children": list(kids)}


def SWITCH(obs, cases, default):
    return {"op": "SWITCH", "obs": obs, "cases": cases, "default": default}


def BUDGET(limit, child):
    return {"op": "BUDGET", "limit_tokens": limit, "child": child}


def STOP(reason):
    return {"op": "STOP", "reason": reason}


def attempt(operator="assigned", report=False):
    """Одна попытка: вызов, проверка, приёмка — конец; иначе дальше по дереву."""
    return SEQ(CALL(operator, report=report), CHECK, SWITCH("violation_subtype", {"none": STOP("accepted")}, CHECK))


def designer(root):
    return config(policies={"designer": {"policy_id": "control", "root": root}})


# ── состояния программы накладных ──

def designing():
    """DESIGN: карточки с «одна валюта у всех строк» — ответ разложения billing проходит П1–П7."""
    s = copy.deepcopy(FX["s_design"])
    s["cards"].update({"app": FX["c_app_fixed"], "app.billing": FX["c_billing_fixed"]})
    s["designs"]["app"] = FX["d_app_fixed"]
    return s


def billing_bad():
    """DESIGN: карточка billing без «одна валюта» — тот же ответ разложения падает на П4 (dependency)."""
    return copy.deepcopy(FX["s_design"])


BILLING = FX["billing_answer"]
BILLING_AGAIN = as_json(json.loads(FX["billing_answer"]))      # то же разложение другой записью: хэш ответа другой


def built(**over):
    """BUILD: всё разложено и принято, кроме сборок; функции приняты."""
    s = copy.deepcopy(FX["s_build"])
    accepted = {"subject": "", "kind": "", "state": "accepted", "attempts": 1, "form_retries": 0, "reports": [], "answer_hashes": []}
    for subject in ["map:app", "design:app", "design:app.billing", "function:app.billing.lines:line_total", "function:app.money:add"]:
        s["elements"][subject] = {**accepted, "subject": subject, "kind": subject.split(":")[0]}
    for subject in ["assembly:app", "assembly:app.billing"]:
        s["elements"][subject] = {**accepted, "subject": subject, "kind": "assembly", "state": "planned", "attempts": 0}
    s.update(over)
    return s


def first_call_of(state, cfg=CFG):
    act = plan_next(state, cfg)
    assert act["kind"] == "call_model", act
    return act["task"]


# ═══ гарантии исполнителя arch2 в пошаговом исполнении ═══

def test_budget_frame_blocks_the_next_call_once_the_task_spent_it():
    """ГАРАНТИЯ 1 arch2: после исчерпания BUDGET вызова нет. Первый ответ стоит 1200 токенов при
    рамке 1000 — следующая починка не зовётся, элемент ждёт пользователя с причиной budget."""
    tight = designer(BUDGET(1000, SEQ(CALL(), CHECK, SWITCH("violation_subtype", {"none": STOP("accepted")},
                                                             attempt("same", report=True)))))
    s = billing_bad()
    t = apply_event(s, answered(first_call_of(s, tight), BILLING), tight)
    el = element(t["state"], "design:app.billing")
    assert el["tokens"] == 1200 and el["policy_path"].startswith("user:budget:")
    assert t["state"]["phase"] == "PAUSED"
    act = plan_next(t["state"], tight)
    assert act["kind"] == "ask_user" and act["question"]["reason"] == "budget"


def test_budget_frame_with_room_lets_the_repair_call_through():
    loose = designer(BUDGET(100000, SEQ(CALL(), CHECK, SWITCH("violation_subtype", {"none": STOP("accepted")},
                                                              attempt("same", report=True)))))
    s = billing_bad()
    t = apply_event(s, answered(first_call_of(s, loose), BILLING), loose)
    act = plan_next(t["state"], loose)
    assert act["kind"] == "call_model" and act["task"]["operator"] == "gemini"
    assert act["task"]["report"]["layer"] == "P4" and act["task"]["attempt"] == 2


def test_budget_is_checked_before_every_call_inside_the_frame():
    """Рамка проверяется у каждого вызова под ней, а не только при входе в неё: вторая попытка
    (1200 < 2000) идёт, третья (2400 ≥ 2000) — нет."""
    frame = designer(BUDGET(2000, SEQ(attempt(), attempt("same", report=True), attempt("same", report=True))))
    s = billing_bad()
    t = apply_event(s, answered(first_call_of(s, frame), BILLING), frame)
    t = apply_event(t["state"], answered(first_call_of(t["state"], frame), BILLING_AGAIN), frame)
    assert element(t["state"], "design:app.billing")["policy_path"].startswith("user:budget:")
    assert plan_next(t["state"], frame)["question"]["reason"] == "budget"


def test_answer_that_crosses_the_budget_is_still_judged():
    """Рамка ограничивает следующие вызовы, а не уже полученный ответ: годный ответ, перешедший
    рамку, принимается."""
    tight = designer(BUDGET(1000, attempt()))
    s = designing()
    t = apply_event(s, answered(first_call_of(s, tight), BILLING), tight)
    assert element(t["state"], "design:app.billing")["state"] == "accepted"


def test_untrusted_pass_is_not_accepted_and_asks_the_user():
    """ГАРАНТИЯ 5 arch2 (I-15): недоверенная проверка не принимает. pass без доверия — «не знаю»:
    политика не двигается, оболочка спрашивает пользователя о перепроверке."""
    s = FX["s_new"]
    t = apply_event(s, answered(first_call_of(s, UNTRUSTED), MAP), UNTRUSTED)
    assert [e["trusted"] for e in t["evidence"]] == [False] * len(t["evidence"])
    assert all(e["verdict"] == "pass" for e in t["evidence"])
    assert element(t["state"], "map:app")["state"] != "accepted"
    act = plan_next(t["state"], UNTRUSTED)
    assert act == {"kind": "ask_user", "question": {"recheck": "map:app", "reason": "unknown"}}


def test_trusted_pass_is_accepted():
    s = FX["s_new"]
    t = apply_event(s, answered(first_call_of(s), MAP))
    assert element(t["state"], "map:app")["state"] == "accepted"
    assert first_call_of(t["state"])["subject"] == "design:app"


def test_untrusted_branch_does_not_close_par_nor_open_the_next():
    """PAR[gemini, grok]: недоверенный pass первой ветви не закрывает PAR (arch2), а «не знаю» в rptg
    и следующую ветвь не запускает — вопрос пользователю, второго вызова нет."""
    portfolio = config(policies={"designer": {"policy_id": "par", "root": PAR(attempt("gemini"), attempt("grok"))}})
    untrusted = load(T.Config, {**FX["cfg"], "policies": {"designer": {"policy_id": "par", "root": PAR(attempt("gemini"), attempt("grok"))}}})
    s = designing()
    task = first_call_of(s, portfolio)
    assert task["operator"] == "gemini"
    t = apply_event(s, answered(task, BILLING), untrusted)
    assert plan_next(t["state"], untrusted)["kind"] == "ask_user"


def test_par_stops_on_the_first_accepted_branch():
    portfolio = config(policies={"designer": {"policy_id": "par", "root": PAR(attempt("gemini"), attempt("grok"))}})
    s = designing()
    t = apply_event(s, answered(first_call_of(s, portfolio), BILLING), portfolio)
    assert element(t["state"], "design:app.billing")["state"] == "accepted"
    act = plan_next(t["state"], portfolio)
    assert not (act["kind"] == "call_model" and act["task"]["subject"] == "design:app.billing")


def test_par_closes_when_a_branch_without_stop_is_accepted():
    """Ветвь PAR кончилась без STOP, но предмет принят — PAR закрыт, следующая ветвь не идёт
    (arch2 test_lazy_stop_on_first_trusted_pass)."""
    plain = config(policies={"designer": {"policy_id": "par", "root": PAR(SEQ(CALL("gemini"), CHECK), SEQ(CALL("grok"), CHECK))}})
    s = designing()
    t = apply_event(s, answered(first_call_of(s, plain), BILLING), plain)
    assert element(t["state"], "design:app.billing")["state"] == "accepted"
    act = plan_next(t["state"], plain)
    assert not (act["kind"] == "call_model" and act["task"]["subject"] == "design:app.billing")


def test_par_failed_branch_moves_to_the_next_branch_from_the_same_card():
    """Ветвь не прошла — следующая ветвь, с той же карточкой и без отчёта первой (ветви не делят
    артефакт, arch2 test_branches_do_not_share_artifact)."""
    portfolio = config(policies={"designer": {"policy_id": "par", "root": PAR(attempt("gemini"), attempt("grok"))}})
    s = billing_bad()
    t = apply_event(s, answered(first_call_of(s, portfolio), BILLING), portfolio)
    task = first_call_of(t["state"], portfolio)
    assert task["subject"] == "design:app.billing" and task["operator"] == "grok"
    assert "report" not in task


def test_stop_ends_before_any_call():
    """STOP завершает всё: вызова нет, причина видна в действии."""
    off = designer(PAR(STOP("designers_off"), attempt()))
    act = plan_next(designing(), off)
    assert act["kind"] == "pause" and "designers_off" in act["reason"]


def test_switch_dispatches_on_the_matching_case_and_falls_back_to_default():
    policy = designer(SEQ(CALL(), CHECK, SWITCH("violation_subtype", {"form": STOP("form_seen")}, STOP("other_seen"))))
    s = billing_bad()
    task = first_call_of(s, policy)
    dep = apply_event(s, answered(task, BILLING), policy)
    assert plan_next(dep["state"], policy)["question"]["reason"] == "other_seen"
    form = apply_event(s, answered(task, "Сейчас разложу узел."), policy)
    assert plan_next(form["state"], policy)["question"]["reason"] == "form_seen"


def test_transition_and_choice_are_deterministic():
    """ГАРАНТИЯ 3 arch2: те же ответы — та же последовательность; порядок ключей состояния роли не
    играет."""
    s = FX["s_billing"]
    a, b = apply_event(s, FX["e_billing"]), apply_event(s, FX["e_billing"])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    flipped = copy.deepcopy(s)
    flipped["elements"] = dict(reversed(list(s["elements"].items())))
    flipped["cards"] = dict(reversed(list(s["cards"].items())))
    c = apply_event(flipped, FX["e_billing"])
    assert json.dumps(c["state"], sort_keys=True) == json.dumps(a["state"], sort_keys=True)
    assert plan_next(a["state"]) == plan_next(c["state"])


def test_invalid_policy_blocks_every_call():
    """Валидатор arch2 до исполнения: CALL без CHECK — никаких вызовов, пауза с проблемой."""
    bad = designer(SEQ(CALL(), STOP("accepted")))
    act = plan_next(FX["s_new"], bad)
    assert act["kind"] == "pause" and "за CALL нет CHECK" in act["reason"]


# ═══ политика по умолчанию (LOGIC §7.3) ═══

MAP = as_json({"map_text": "# Карта app\n\nДва узла: накладные и деньги.\n", "card": FX["c_app_fixed"],
               "types": [FX["t_money"], FX["t_line"], FX["t_order"], FX["t_invoice"]]})


def test_dependency_failure_goes_to_the_next_rung_with_the_report():
    t = apply_event(FX["s_billing"], FX["e_billing"])
    task = first_call_of(t["state"])
    assert (task["operator"], task["attempt"], task["wording"]) == ("grok", 2, "primary")
    assert (task["report"]["layer"], task["report"]["rule"]) == ("P4", "I13")


def test_form_is_retried_by_the_same_operator_and_does_not_spend_attempts():
    """Форма: та же модель, другая формулировка, попытка содержания не тратится (эксп. 12); повторы
    формы кончились — лестница идёт дальше, а не в подозрение; у карты лестница — один архитектор,
    поэтому дальше — вопрос пользователю (§7.8)."""
    s = FX["s_map"]
    texts = ["Сейчас подумаю над архитектурой.", "Ещё немного подумаю.", "Почти готово."]
    journal = []
    for i, text in enumerate(texts):
        task = FX["task_map"] if i == 0 else first_call_of(s)
        if i:
            assert (task["operator"], task["wording"], task["attempt"]) == ("opus", "alternative", 1)
            assert "report" not in task
        t = apply_event(s, answered(task, text))
        s, journal = t["state"], journal + t["journal"]
        assert element(s, "map:app")["attempts"] == 1
    el = element(s, "map:app")
    assert el["form_retries"] == 2 and el["policy_path"].startswith("user:exhausted:")
    assert "suspect" not in [k for k, _ in kinds(journal)]
    assert plan_next(s)["question"]["reason"] == "exhausted"


def test_repeated_answer_is_not_an_attempt():
    """Повтор по хэшу — не попытка (эксп. 10): позиция и счётчики прежние, запись repeat, тот же вызов."""
    first = apply_event(FX["s_map"], FX["e_form"])
    task = first_call_of(first["state"])
    again = apply_event(first["state"], answered(task, FX["e_form"]["answer"]["text"]))
    before, after = element(first["state"], "map:app"), element(again["state"], "map:app")
    assert (after["attempts"], after["form_retries"], after["policy_path"]) == (before["attempts"], before["form_retries"], before["policy_path"])
    assert ("repeat", "map:app") in kinds(again["journal"])
    assert first_call_of(again["state"]) == task


# ═══ подозрение на карточку и ревизия владельца (§7.5), остановки (§7.8) ═══

def suspected():
    """billing: П4 на ступени 1, тот же провал на ступени 2 — подозрение, владелец app переоткрыт."""
    s = FX["s_billing"]
    t = apply_event(s, FX["e_billing"])
    t = apply_event(t["state"], answered(first_call_of(t["state"]), BILLING_AGAIN))
    return t


def test_same_failure_on_the_next_rung_suspects_the_card_and_reopens_the_owner():
    t = suspected()
    el, owner = element(t["state"], "design:app.billing"), element(t["state"], "design:app")
    assert el["state"] == "card_suspect"
    assert owner["state"] == "repairing" and owner["reports"][0]["layer"] == "P4"
    assert ("suspect", "design:app.billing") in kinds(t["journal"])
    task = first_call_of(t["state"])
    assert (task["subject"], task["kind"], task["role"]) == ("design:app", "revision", "architect")
    assert task["report"]["subject"] == "design:app.billing"


def keep_card(t):
    """Владелец оставляет карточку: то же разложение корня; корень — на утверждение, «да»."""
    t = apply_event(t["state"], answered(first_call_of(t["state"]), design_text(FX["d_app"])))
    act = plan_next(t["state"])
    assert act["kind"] == "ask_user" and act["question"]["approve"] == "app"
    return apply_event(t["state"], user(**act["question"], decision="yes"))


def test_owner_keeps_the_card_and_the_ladder_resumes_where_suspicion_stopped_it():
    """Оставить карточку — лестница снизу продолжается с места раннего подозрения: ступень 3."""
    t = keep_card(suspected())
    el = element(t["state"], "design:app.billing")
    assert el["state"] != "card_suspect" and el["round"] == 1
    task = first_call_of(t["state"])
    assert (task["subject"], task["operator"]) == ("design:app.billing", "opus")
    assert task["report"]["layer"] == "P4"


def test_same_failure_after_a_kept_card_is_a_repeated_state_and_pauses():
    """Повтор состояния: после круга подозрения — тот же провал; PAUSED, вопрос пользователю."""
    t = keep_card(suspected())
    t = apply_event(t["state"], answered(first_call_of(t["state"]), BILLING_AGAIN + "\n"))
    assert element(t["state"], "design:app.billing")["policy_path"].startswith("user:repeat:")
    assert t["state"]["phase"] == "PAUSED"
    act = plan_next(t["state"])
    assert act["kind"] == "ask_user" and act["question"]["reason"] == "repeat"


def test_owner_revises_the_card_and_the_suspect_starts_over_on_the_new_card():
    """Ревизия карточки: зависимое устаревает (§7.7); у подозреваемого нет принятой версии — он
    начинается заново на новой карточке: новое назначение, без старых отчётов."""
    s = copy.deepcopy(FX["s_billing"])
    s["cards"]["app"] = FX["c_app_fixed"]
    t = apply_event(s, FX["e_billing"])
    t = apply_event(t["state"], answered(first_call_of(t["state"]), BILLING_AGAIN))
    t = apply_event(t["state"], answered(first_call_of(t["state"]), design_text(FX["d_app_fixed"])))
    act = plan_next(t["state"])
    t = apply_event(t["state"], user(**act["question"], decision="yes"))
    el = element(t["state"], "design:app.billing")
    assert el["state"] == "planned" and el["reports"] == [] and "assignment" not in el
    task = first_call_of(t["state"])
    assert (task["subject"], task["operator"], task["wording"]) == ("design:app.billing", "gemini", "primary")
    assert "report" not in task
    t = apply_event(t["state"], answered(task, BILLING))
    assert element(t["state"], "design:app.billing")["state"] == "accepted"


def test_rejected_revision_leaves_nothing_of_the_rejected_subtree():
    """«Нет» ревизии утверждённого разложения корня: разложение и карточки детей сняты, карта
    переоткрыта с комментарием; элементы под корнем принадлежали отвергнутой версии — их нет,
    следующая версия разведёт детей заново (код функций перепроверится без модели)."""
    s = copy.deepcopy(FX["s_billing"])
    s["cards"]["app"] = FX["c_app_fixed"]
    t = apply_event(s, FX["e_billing"])
    t = apply_event(t["state"], answered(first_call_of(t["state"]), BILLING_AGAIN))
    t = apply_event(t["state"], answered(first_call_of(t["state"]), design_text(FX["d_app_fixed"])))
    act = plan_next(t["state"])
    t = apply_event(t["state"], user(**act["question"], decision="no", comment="деньги — отдельным узлом"))
    assert sorted(t["state"]["elements"]) == ["design:app", "map:app"]
    assert t["state"]["phase"] == "MAP"
    task = first_call_of(t["state"])
    assert task["subject"] == "map:app" and task["report"]["expected"] == "деньги — отдельным узлом"


def test_revision_returning_to_the_version_before_last_is_an_oscillation():
    """Колебание ревизий (§7.8): разложение вернулось к версии двумя ревизиями ранее — PAUSED,
    вопрос пользователю."""
    a, b = FX["d_billing"], copy.deepcopy(FX["d_billing"])
    b["children"][0]["purpose"] = "стоимость одной строки накладной"
    ha, hb = lang.digest(value=a), lang.digest(value=b)
    s = built(phase="BUILD")
    s["designs"]["app.billing"] = b
    s["cards"]["app.billing.lines"] = b["children"][0]
    s["elements"]["design:app.billing"].update(state="repairing", policy_path="reopen:root", versions=[ha, hb],
                                               assignment=FX["as_billing"], reports=[FX["r_currency"]])
    t = apply_event(s, answered(first_call_of(s), design_text(a)))
    el = element(t["state"], "design:app.billing")
    assert el["policy_path"].startswith("user:oscillation:") and el["versions"][-1] == ha
    assert ("oscillation", "design:app.billing") in kinds(t["journal"])
    assert t["state"]["phase"] == "PAUSED" and plan_next(t["state"])["question"]["reason"] == "oscillation"


def test_new_version_is_not_an_oscillation():
    a, b = FX["d_billing"], copy.deepcopy(FX["d_billing"])
    b["children"][0]["purpose"] = "стоимость одной строки накладной"
    s = built(phase="BUILD")
    s["designs"]["app.billing"] = b
    s["cards"]["app.billing.lines"] = b["children"][0]
    s["elements"]["design:app.billing"].update(state="repairing", policy_path="reopen:root", versions=[lang.digest(value=b)],
                                               assignment=FX["as_billing"], reports=[FX["r_currency"]])
    t = apply_event(s, answered(first_call_of(s), design_text(a)))
    assert element(t["state"], "design:app.billing")["state"] == "accepted"
    assert t["state"]["phase"] != "PAUSED"


# ═══ устаревание (§7.7), «не знаю» и перепроверка ═══

def test_revised_child_card_rechecks_the_function_without_a_model(tmp_path):
    """Устаревание ≠ ошибка (F37, F38): у функции изменилась карточка — код перепроверяется
    проверками, модель не зовётся; дальше — прогоны песочницы, и функция снова принята."""
    revised = copy.deepcopy(FX["d_billing"])
    revised["children"][0]["ops"][0]["examples"].append(
        {"in": {"line": {"qty": 1, "price": "3.50", "currency": "EUR"}}, "out": {"amount": "3.50", "currency": "EUR"}, "source": "model"})
    s = built(phase="BUILD")
    s["elements"]["design:app.billing"].update(state="repairing", policy_path="reopen:root", assignment=FX["as_billing"],
                                               reports=[FX["r_currency"]])
    t = apply_event(s, answered(first_call_of(s), design_text(revised)))
    fn = element(t["state"], "function:app.billing.lines:line_total")
    assert fn["state"] == "checking" and fn["policy_path"].startswith("recheck:")
    state, trail = drive(t["state"], lambda task: pytest.fail(f"модель не должна зваться: {task}"), tmp_path, steps=2)
    assert [a["kind"] for _, a in trail[:2]] == ["run_sandbox", "run_sandbox"]
    assert element(state, "function:app.billing.lines:line_total")["state"] == "accepted"


def test_user_recheck_after_unknown_accepts_without_a_model():
    """ERROR ≠ FAIL: «не знаю» ждёт пользователя; перепроверка после того, как проверки стали
    доверенными, принимает сохранённый ответ без вызова модели."""
    s = designing()
    t = apply_event(s, answered(first_call_of(s, UNTRUSTED), BILLING), UNTRUSTED)
    act = plan_next(t["state"], UNTRUSTED)
    assert act["question"] == {"recheck": "design:app.billing", "reason": "unknown"}
    t = apply_event(t["state"], user(recheck="design:app.billing"))
    assert element(t["state"], "design:app.billing")["state"] == "accepted"


def test_user_recheck_of_the_map_accepts_without_a_model():
    s = FX["s_new"]
    t = apply_event(s, answered(first_call_of(s, UNTRUSTED), MAP), UNTRUSTED)
    t = apply_event(t["state"], user(recheck="map:app"))
    assert element(t["state"], "map:app")["state"] == "accepted"
    assert first_call_of(t["state"])["subject"] == "design:app"


# ═══ повышение листа (§7.4) ═══

LT_WRONG = "def line_total(line: InvoiceLine) -> Money:\n    return Money(amount=line.qty + line.price, currency=line.currency)\n"


def last_rung():
    """Функция line_total на последней ступени лестницы исполнителей (opus, ступень 4)."""
    s = built(phase="BUILD")
    s["elements"]["function:app.billing.lines:line_total"] = {
        "subject": "function:app.billing.lines:line_total", "kind": "function", "state": "escalated", "attempts": 3,
        "form_retries": 0, "reports": [], "answer_hashes": [], "policy_path": "root/seq[3]/seq[0]",
        "assignment": {"subject": "function:app.billing.lines:line_total", "role": "implementer", "class": "compute",
                       "operator": "opus", "rung": 4, "decided_by": "prior"}}
    return s


@pytest.fixture(scope="module")
def exhausted_function(tmp_path_factory):
    """Неверный код на последней ступени: статика проходит, прогоны — Э2/Э3 fail."""
    tmp = tmp_path_factory.mktemp("rung4")
    s = last_rung()
    task = first_call_of(s)
    assert (task["operator"], task["attempt"]) == ("opus", 4)
    t = apply_event(s, answered(task, code_text(LT_WRONG)))
    act = plan_next(t["state"])
    assert act["kind"] == "run_sandbox" and act["run"] == "e1_mypy"
    t = apply_event(t["state"], sandbox(t["state"], act, tmp))
    act = plan_next(t["state"])
    assert act["kind"] == "run_sandbox" and act["run"] == "e2_e3"
    return t["state"], sandbox(t["state"], act, tmp)


def test_function_that_the_whole_ladder_failed_is_promoted(exhausted_function):
    state, event = exhausted_function
    t = apply_event(state, event)
    assert element(t["state"], "function:app.billing.lines:line_total")["state"] == "promoted"
    assert element(t["state"], "design:app.billing.lines")["state"] == "planned"
    assert ("promotion", "design:app.billing.lines") in kinds(t["journal"])
    task = first_call_of(t["state"])
    assert (task["subject"], task["kind"], task["role"]) == ("design:app.billing.lines", "design", "designer")


def test_at_max_depth_promotion_is_impossible_and_the_card_is_suspected(exhausted_function):
    state, event = exhausted_function
    shallow = config(limits={**FX["cfg"]["limits"], "max_depth": 3})
    t = apply_event(state, event, shallow)
    assert element(t["state"], "function:app.billing.lines:line_total")["state"] == "card_suspect"
    assert element(t["state"], "design:app.billing")["state"] == "repairing"
    assert ("suspect", "function:app.billing.lines:line_total") in kinds(t["journal"])


# ═══ сборка: очередь и вина в Э6 ═══

def test_assembly_waits_until_all_its_children_are_accepted():
    """Сборки — снизу вверх и только над принятыми детьми (§7.1): функция денег ждёт пользователя —
    сборка корня в очередь не встаёт, оболочка спрашивает о функции."""
    s = built(phase="BUILD")
    s["elements"]["assembly:app.billing"]["state"] = "accepted"
    s["elements"]["function:app.money:add"].update(state="checking", policy_path="user:unknown:root/seq[0]/seq[1]")
    assert plan_next(s) == {"kind": "ask_user", "question": {"recheck": "function:app.money:add", "reason": "unknown"}}


def test_e6_failure_reopens_the_blamed_design(tmp_path):
    """Дыра в схеме узла (две валюты в одной сумме): Э6 fail, виновна схема billing — она
    переоткрывается с отчётом сборки (LOGIC §5, таблица вины)."""
    s = built(phase="BUILD")
    s["cards"]["app.billing"] = FX["c_billing"]
    act = plan_next(s)
    assert act == {"kind": "run_sandbox", "target": {"kind": "node_package", "subject": "app.billing"}, "run": "e6"}
    t = apply_event(s, sandbox(s, act, tmp_path))
    owner = element(t["state"], "design:app.billing")
    assert owner["state"] == "repairing" and owner["reports"][0]["layer"] == "E6"
    assert ("blame", "design:app.billing") in kinds(t["journal"])
    task = first_call_of(t["state"])
    assert (task["subject"], task["kind"]) == ("design:app.billing", "revision")


# ═══ мёртвые операции (§7.6), утверждение (§7.1), команды и бюджет (§7.8) ═══

def test_dead_operations_are_removed_once_the_tree_is_designed():
    """app.money:sub никто не вызывает: после приёмки последнего разложения она снимается каскадом,
    запись revision; карточка ребёнка корня изменилась — разложение корня снова на утверждении."""
    s = copy.deepcopy(FX["s_dead"])
    s["phase"] = "DESIGN"
    s["code"] = {}
    s["elements"] = {"map:app": FX["el_map_ok"], "design:app": FX["el_app_ok"],
                     "design:app.billing": {"subject": "design:app.billing", "kind": "design", "state": "writing",
                                            "assignment": FX["as_billing"], "attempts": 1, "form_retries": 0, "reports": [],
                                            "answer_hashes": []}}
    del s["designs"]["app.billing"]
    del s["cards"]["app.billing.lines"]
    t = apply_event(s, answered(FX["task_billing"], BILLING))
    assert [o["name"] for o in t["state"]["cards"]["app.money"]["ops"]] == ["add"]
    assert any(j["kind"] == "revision" and j["data"]["removed"] == ["app.money:sub"] for j in t["journal"])
    assert element(t["state"], "design:app")["state"] == "approval" and t["state"]["phase"] == "MAP_REVIEW"


def test_root_rejection_reopens_the_map_with_the_comment():
    digest = plan_next(FX["s_review"])["question"]["design_hash"]
    t = apply_event(FX["s_review"], user(approve="app", design_hash=digest, decision="no", comment="итог — в валюте заказа"))
    assert t["state"]["phase"] == "MAP" and "app" not in t["state"]["designs"]
    task = first_call_of(t["state"])
    assert task["subject"] == "map:app" and task["report"]["expected"] == "итог — в валюте заказа"


def test_reply_to_a_stale_approval_changes_nothing():
    t = apply_event(FX["s_review"], user(approve="app", design_hash="0" * 64, decision="yes"))
    assert t["state"]["elements"] == FX["s_review"]["elements"] and t["state"]["phase"] == "MAP_REVIEW"
    assert ("stale_reply", "design:app") in kinds(t["journal"])


def test_pause_and_resume_commands():
    t = apply_event(FX["s_design"], command("pause"))
    assert t["state"]["phase"] == "PAUSED" and plan_next(t["state"])["kind"] == "pause"
    t = apply_event(t["state"], command("resume"))
    assert t["state"]["phase"] == "DESIGN" and first_call_of(t["state"])["subject"] == "design:app.billing"


def test_spent_budget_pauses_and_a_new_limit_resumes():
    s = copy.deepcopy(FX["s_design"])
    s["budget"] = {"limit": "1.00", "spent": "1.0000001"}
    act = plan_next(s)
    assert act == {"kind": "pause", "reason": "бюджет исчерпан"}
    t = apply_event(s, command("budget", limit="5.00"))
    assert t["state"]["budget"]["limit"] == "5.00"
    assert first_call_of(t["state"])["subject"] == "design:app.billing"


# ═══ сквозной круг: программа накладных от замысла до DONE ═══

ANSWERS = {
    "map:app": MAP,
    "design:app": design_text(FX["d_app_fixed"]),
    "design:app.billing": design_text(FX["d_billing"]),
    "function:app.billing.lines:line_total": code_text(FX["code_lt"]),
    "function:app.money:add": code_text(FX["code_add"]),
}


def test_invoice_program_from_idea_to_done(tmp_path):
    """Пять ответов моделей, одно утверждение, шесть прогонов песочницы: NEW → MAP → MAP_REVIEW →
    DESIGN → BUILD → E2E → DONE; каждая функция — сначала mypy, потом примеры и свойства; сборки —
    снизу вверх; корень — пробный запуск."""
    state, trail = drive(FX["s_new"], lambda task: ANSWERS[task["subject"]], tmp_path)
    assert state["phase"] == "DONE" and trail[-1][1] == {"kind": "stop"}
    calls = [a["task"]["subject"] for _, a in trail if a["kind"] == "call_model"]
    assert calls == ["map:app", "design:app", "design:app.billing", "function:app.billing.lines:line_total", "function:app.money:add"]
    runs = [(a["target"]["subject"], a["run"]) for _, a in trail if a["kind"] == "run_sandbox"]
    assert runs == [("app.billing.lines:line_total", "e1_mypy"), ("app.billing.lines:line_total", "e2_e3"),
                    ("app.money:add", "e1_mypy"), ("app.money:add", "e2_e3"), ("app.billing", "e6"), ("app", "smoke")]
    phases = [p for p, _ in trail]
    assert [p for i, p in enumerate(phases) if i == 0 or phases[i - 1] != p] == ["NEW", "MAP", "MAP_REVIEW", "DESIGN", "BUILD", "E2E", "DONE"]
    assert all(e["state"] == "accepted" for e in state["elements"].values())
    assert state["approvals"]["app"] == lang.digest(value=FX["d_app_fixed"])
