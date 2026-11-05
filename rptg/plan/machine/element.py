"""Лист rptg.plan.machine.element — элемент после шага политики (LOGIC §7.2), утверждение
пользователя (§7.1) и решения, перепроверка, команды оболочки (§7.5, §7.8).

Функции приняты по карточке design/rptg.plan.machine.yaml; обвязку пишет скрипт. Состояние — JSON;
отчёты приходят записью JSON. Утверждение и прочие ответы пользователя — две работы, две операции
(после Э1 01.10.2026: в одной функции решений было 29 при допуске 24,5).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import JournalEntry
from rptg.plan._types import Absorbed

if TYPE_CHECKING:
    from rptg._types import Config, Json, Override, Sha
    from rptg.plan._types import EventFacts, Obs, PolicyStep


def update(state: Json, facts: EventFacts, obs: Obs, step: PolicyStep, reports: Json, manual: Override,
           design_hash: Sha) -> Absorbed:
    """Шаг none — элемент как есть. Провал — отчёты и подтип провала; приёмка — отчётов нет, подтип
    none. Вызов: повтор — позиция и состояние прежние, запись repeat; иначе позиция шага, назначение —
    оператор и ступень шага, состояние: alternative — form_retry и form_retries + 1, ступень выше —
    escalated, иначе с отчётом — repairing, иначе planned. check — checking. stop: accepted —
    approval у разложения корня и узла с ручным approve, иначе accepted; unknown — checking и
    ожидание пользователя; exhausted и card_suspect — card_suspect; blame — planned; reopen —
    repairing и переоткрытие; прочая причина — card_suspect и ожидание пользователя. route — узел
    принятого разложения."""
    subject, notes = facts.subject, []
    if step.wait == "none":
        return Absorbed(state=state, facts=facts, obs=obs, step=step, route="", design_hash=design_hash, notes=[])
    el, kind = dict(state["elements"][subject]), subject.partition(":")[0]
    a = el.get("assignment") or {}
    approve = kind == "design" and (facts.level == 1 or bool(manual.approve))

    def called():
        if obs.repeat:
            notes.append(JournalEntry(kind="repeat", subject=subject))
            return el["state"]
        if step.wording == "alternative":
            el["form_retries"] += 1
            return "form_retry"
        higher = step.rung > (a.get("rung") or step.rung) or step.operator != a.get("operator", step.operator)
        return "escalated" if higher else "repairing" if step.report else "planned"

    def stopped():
        table = {"accepted": ("approval" if approve else "accepted", step.path), "unknown": ("checking", f"user:unknown:{step.path}"),
                 "exhausted": ("card_suspect", step.path), "card_suspect": ("card_suspect", step.path), "blame": ("planned", step.path),
                 "reopen": ("repairing", "reopen:root")}
        return table.get(step.stop, ("card_suspect", f"user:{step.stop}:{step.path}"))

    if facts.failures:
        el["reports"], el["last_subtype"] = list(reports), obs.subtype
    elif obs.accepted:
        el["reports"], el["last_subtype"] = [], "none"
    if step.wait == "call":
        el["state"], el["policy_path"], el["assignment"] = called(), step.path, {**a, "operator": step.operator, "rung": step.rung}
    elif step.wait == "check":
        el["state"], el["policy_path"] = "checking", step.path
    else:
        el["state"], el["policy_path"] = stopped()
    state = {**state, "elements": {**state["elements"], subject: el}}
    route = facts.node if kind == "design" and el["state"] == "accepted" else ""
    return Absorbed(state=state, facts=facts, obs=obs, step=step, route=route, design_hash=design_hash, notes=notes)


def reply(absorbed: Absorbed, cfg: Config) -> Absorbed:
    """Прочие события — как есть. Утверждение {approve, design_hash, decision}: элемент не на
    утверждении или дайджест не тот — запись stale_reply; yes — разложение принято, утверждение
    записано (версию записала ревизия по ответу), route — узел; no — разложение и карточки его детей
    сняты, элементы поддерева тоже (они принадлежали отвергнутой версии; следующая разведёт детей
    заново), отчёт с комментарием:
    у корня карта переоткрывается с ним, разложение корня — заново; у поддерева переоткрывается
    разложение."""
    f = absorbed.facts
    r = f.reply
    if f.event != "user_answered" or "approve" not in r:
        return absorbed
    s, notes, route = dict(absorbed.state), list(absorbed.notes), absorbed.route
    els, x = dict(s["elements"]), r["approve"]
    key, root = f"design:{x}", next((c for c in s["cards"] if "." not in c), "")
    el = els.get(key) or {}

    def reject():
        gone = {c["id"] for c in s["designs"][x]["children"]}
        s["designs"] = {k: v for k, v in s["designs"].items() if k != x}
        s["cards"] = {k: v for k, v in s["cards"].items() if k not in gone}
        back = f"map:{root}" if x == root else key
        told = {"subject": back, "layer": "P7", "rule": "user", "where": "ответ пользователя", "means": "пользователь отклонил разложение",
                "expected": str(r.get("comment") or "правка по замечанию пользователя")}
        for k in [k for k in els if k.split(":")[1].startswith(x + ".")]:
            del els[k]
        els[back] = {**els[back], "state": "repairing", "reports": [told], "policy_path": "reopen:root"}
        if x == root:
            els[key] = {**el, "state": "planned", "policy_path": "", "reports": []}

    if el.get("state") != "approval" or r.get("design_hash") != absorbed.design_hash:
        notes.append(JournalEntry(kind="stale_reply", subject=key))
    elif r.get("decision") == "yes":
        s["approvals"] = {**s["approvals"], x: absorbed.design_hash}
        els[key], route = {**el, "state": "accepted"}, x
    else:
        reject()
    s["elements"] = els
    return Absorbed(state=s, facts=f, obs=absorbed.obs, step=absorbed.step, route=route, design_hash=absorbed.design_hash, notes=notes)


def decide(absorbed: Absorbed, cfg: Config) -> Absorbed:
    """Прочие события — как есть. Решение {decide, decision} по элементу, что ждёт пользователя: retry —
    элемент переоткрывается; revise — владелец (разложение родителя, у узла корня — корень)
    переоткрывается с отчётами элемента и комментарием, элемент ждёт владельца с прежней позицией.
    Перепроверка {recheck}: unknown на текущем хэше сняты, элемент stale с прежней позицией. Команда
    budget — новый лимит; на каждую команду — запись command."""
    f = absorbed.facts
    r, s, notes = f.reply, dict(absorbed.state), list(absorbed.notes)
    els = dict(s["elements"])
    target = r.get("decide") or r.get("recheck") if f.event == "user_answered" else None

    def recheck(el, back):
        evs = s["evidence"].get(target, [])
        s["evidence"] = {**s["evidence"], target: [e for e in evs if e["verdict"] != "unknown" or e["subject_hash"] != evs[-1]["subject_hash"]]}
        els[target] = {**el, "state": "stale", "policy_path": back}

    def revise(el, back):
        owner = "design:" + (target.split(":")[1].rpartition(".")[0] or target.split(":")[1])
        told = {"subject": target, "layer": "P7", "rule": "user", "where": "ответ пользователя",
                "expected": str(r.get("comment") or "ревизия карточки"), "means": "пользователь просит ревизию карточки"}
        els[owner] = {**els[owner], "state": "repairing", "policy_path": "reopen:root", "reports": el["reports"] + [told]}
        els[target] = {**el, "state": "card_suspect", "policy_path": back}

    if target in els:
        el = els[target]
        back = (el.get("policy_path") or "").split(":", 2)[-1]
        if "recheck" in r:
            recheck(el, back)
        elif r.get("decision") == "retry":
            els[target] = {**el, "state": "repairing", "policy_path": "reopen:root"}
        else:
            revise(el, back)
    if f.event == "command":
        s["budget"] = {**s["budget"], "limit": str(r["limit"])} if r.get("command") == "budget" else s["budget"]
        notes.append(JournalEntry(kind="command", subject=f.subject, data={"command": r.get("command")}))
    s["elements"] = els
    return Absorbed(state=s, facts=f, obs=absorbed.obs, step=absorbed.step, route=absorbed.route, design_hash=absorbed.design_hash,
                    notes=notes)
