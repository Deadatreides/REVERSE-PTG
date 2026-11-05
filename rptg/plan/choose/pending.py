"""Лист rptg.plan.choose.pending — что делать дальше и действие по выбору (plan:pick).

Функции приняты по карточке design/rptg.plan.choose.yaml; обвязку пишет скрипт. Выбор ничего не
пишет; вызов модели берётся по шагу политики, который считает тот же исполнитель, что и переход.
Бюджет — десятичные записи: модуль decimal узлу не разрешён, сравнение точное — в целых.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Action, BuildTarget, Report, Task
from rptg.plan.choose._types import Choice

if TYPE_CHECKING:
    from rptg._types import Assignments, Candidates, Config, Json, Sha
    from rptg.plan._types import Policies, PolicyStep


def choose(state: Json, candidates: Candidates, assignments: Assignments, policies: Policies, cfg: Config) -> Choice:
    """По порядку: DONE — stop; PAUSED — первый ждущий пользователя (ask), иначе pause; adapt или
    explore > 0 — pause (вне этой постройки); у политик нарушения — pause с ними; MAP_REVIEW —
    approve разложения корня; бюджет исчерпан — pause; кандидат — первый: сборка — sandbox (корень —
    program и smoke, иначе node_package и e6), функция на проверке — sandbox по недостающему на
    текущем хэше (нет Э1 от mypy — e1_mypy, иначе e2_e3), прочее — model с назначением кандидата;
    иначе разложение на утверждении — approve; ждущий пользователя — ask; иначе pause."""
    els, phase = state["elements"], state["phase"]
    root = next((c for c in state["cards"] if "." not in c), None) or next(iter(state["user_examples"]), ":").split(":")[0]
    waiting = sorted(k for k, e in els.items() if (e.get("policy_path") or "").startswith("user:"))
    blank = {"subject": "", "role": "", "reason": "", "question": {}, "target": None, "run": "", "assignments": [], "design": {}}

    def made(act, **kw):
        return Choice(act=act, **{**blank, **kw})

    def ask(subject):
        why = els[subject]["policy_path"].split(":")[1]
        question = {"recheck": subject, "reason": why} if why == "unknown" else \
            {"decide": subject, "reason": why, "reports": els[subject].get("reports", [])}
        return made("ask", subject=subject, question=question)

    def num(text):
        whole, _, frac = text.lstrip("-").partition(".")
        return (-1 if text.startswith("-") else 1) * int(whole + (frac + "0" * 18)[:18])

    def first(c, a):
        node = c.subject.split(":")[1]
        evs = state["evidence"].get(c.subject, [])
        mypy = {v["subject_hash"] for v in evs if v["check"] == "E1" and v["tool"] == "mypy"}
        if c.kind == "assembly":
            kind, run = ("program", "smoke") if node == root else ("node_package", "e6")
            return made("sandbox", subject=c.subject, role=c.role, target=BuildTarget(kind=kind, subject=node), run=run)
        if els.get(c.subject, {}).get("state") == "checking":
            return made("sandbox", subject=c.subject, role=c.role, target=BuildTarget(kind="function_tests", subject=c.subject.split(":", 1)[1]),
                        run="e2_e3" if evs and evs[-1]["subject_hash"] in mypy else "e1_mypy")
        return made("model", subject=c.subject, role=c.role, assignments=[a])

    def idle():
        approvals = sorted(k for k, e in els.items() if e["state"] == "approval")
        if approvals:
            return made("approve", subject=approvals[0], role="designer", design=state["designs"].get(approvals[0].split(":")[1], {}))
        return ask(waiting[0]) if waiting else made("pause", reason="нет готовых задач")

    gates = [(phase == "DONE", lambda: made("stop")),
             (phase == "PAUSED", lambda: ask(waiting[0]) if waiting else made("pause", reason="пауза")),
             (cfg.routing.adapt or cfg.routing.explore > 0, lambda: made("pause", reason="routing.adapt и routing.explore в этой постройке не поддержаны")),
             (bool(policies.problems), lambda: made("pause", reason="политика: " + "; ".join(policies.problems))),
             (phase == "MAP_REVIEW", lambda: made("approve", subject=f"design:{root}", role="architect", design=state["designs"].get(root, {}))),
             (num(state["budget"]["spent"]) >= num(state["budget"]["limit"]), lambda: made("pause", reason="бюджет исчерпан")),
             (bool(candidates), lambda: first(candidates[0], assignments[0]))]
    return next((then() for hit, then in gates if hit), None) or idle()


def action(state: Json, choice: Choice, step: PolicyStep, hash: Sha) -> Action:
    """stop, pause — действие с причиной (у stop без причины); approve — ask_user {approve: узел,
    design_hash}; ask — ask_user с вопросом выбора; sandbox — run_sandbox с целью и прогоном; model —
    шаг ждёт вызова: задача (вид: map, design, revision — есть версия разложения узла, function),
    роль, оператор и формулировка шага, попытка = попытки элемента + 1, у alternative — без прибавки,
    отчёт — первый отчёт элемента, если шаг его просит; шаг не ждёт вызова — pause с причиной."""
    def task():
        e = state["elements"].get(choice.subject) or {}
        kind, _, rest = choice.subject.partition(":")
        reports = e.get("reports") or []
        return Task(subject=choice.subject, kind="revision" if kind == "design" and rest in state["designs"] else kind, role=choice.role,
                    operator=step.operator, attempt=e.get("attempts", 0) + (0 if step.wording == "alternative" else 1),
                    wording=step.wording, report=Report(**reports[0]) if step.report and reports else None)

    acts = {"stop": lambda: Action(kind="stop"), "pause": lambda: Action(kind="pause", reason=choice.reason),
            "approve": lambda: Action(kind="ask_user", question={"approve": choice.subject.split(":")[1], "design_hash": hash}),
            "ask": lambda: Action(kind="ask_user", question=choice.question),
            "sandbox": lambda: Action(kind="run_sandbox", target=choice.target, run=choice.run),
            "model": lambda: Action(kind="call_model", task=task()) if step.wait == "call" else
            Action(kind="pause", reason=f"{choice.subject}: шаг политики не ждёт вызова ({step.wait} {step.stop})")}
    return acts[choice.act]()
