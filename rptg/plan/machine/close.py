"""Лист rptg.plan.machine.close — фаза проекта (LOGIC §7.1, §7.8) и итог перехода с журналом.

Функции приняты по карточке design/rptg.plan.machine.yaml; обвязку пишет скрипт. Состояние и итог —
JSON: к типу Transition их приводит обвязка на выходе схемы. Фаза идёт вперёд по состояниям
элементов, назад — только по утверждению корня; правду о поддеревьях показывают элементы.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Config, Json
    from rptg.plan._types import Absorbed, Settled


def phase(before: Json, absorbed: Absorbed, settled: Settled, cfg: Config) -> Json:
    """Фаза вперёд по состояниям: NEW → MAP с первым событием карты; разложение корня на утверждении —
    MAP_REVIEW; «нет» утверждения корня — MAP; DESIGN, пока есть непринятые разложения; BUILD — все
    разложения приняты; E2E — приняты функции и сборки кроме корня; DONE — принята сборка корня.
    PAUSED — команда pause или элемент ждёт пользователя из-за колебания, повтора состояния или
    бюджета задачи; из PAUSED выводит resume или ответ пользователя. DONE не меняется."""
    s, f = settled.state, absorbed.facts
    els, now = s["elements"], s["phase"]
    root = next((c for c in s["cards"] if "." not in c), "")
    command = f.reply.get("command") if f.event == "command" else None
    stuck = any((e.get("policy_path") or "").startswith(("user:oscillation", "user:repeat", "user:budget")) for e in els.values())

    def all_of(prefix, skip=""):
        return all(e["state"] == "accepted" for k, e in els.items() if k.startswith(prefix) and k != skip)

    def found():
        if els.get(f"design:{root}", {}).get("state") != "accepted":
            return "MAP"
        if not all_of("design:"):
            return "DESIGN"
        if not (all_of("function:") and all_of("assembly:", f"assembly:{root}")):
            return "BUILD"
        return "E2E" if els.get(f"assembly:{root}", {}).get("state") != "accepted" else "DONE"

    def forward():
        order = ["NEW", "MAP", "MAP_REVIEW", "DESIGN", "BUILD", "E2E", "DONE"]
        return max(found(), "NEW" if now == "PAUSED" else now, key=order.index)

    def next_phase():
        if command == "pause" or stuck:
            return "PAUSED"
        if els.get(f"design:{root}", {}).get("state") == "approval":
            return "MAP_REVIEW"
        rejected = f.event == "user_answered" and f.reply.get("approve") == root and f.reply.get("decision") != "yes"
        return "MAP" if rejected else forward()

    held = now == "DONE" or now == "PAUSED" and command != "resume" and f.event != "user_answered" and not stuck
    return s if held else {**s, "phase": next_phase()}


def journal(before: Json, after: Json, absorbed: Absorbed, settled: Settled, evidence: Json) -> Json:
    """Итог: состояние после, доказательства события как есть; журнал — по записи evidence на
    доказательство события, записи впитывания и следствий, по записи state на каждый изменившийся
    элемент (предмет, было, стало) по порядку предметов, запись phase при смене фазы, запись budget
    при смене расхода, запись outcome на каждый элемент, пришедший в accepted, promoted или
    card_suspect."""
    entries = [{"kind": "evidence", "subject": e["subject"], "data": {"check": e["check"], "verdict": e["verdict"]}} for e in evidence]
    entries += [{"kind": n.kind, "subject": n.subject, "data": n.data} for n in settled.notes]
    old, new = before["elements"], after["elements"]
    for subject in sorted(old.keys() | new.keys()):
        was, now = old.get(subject) or {}, new.get(subject) or {}
        if was != now:
            entries.append({"kind": "state", "subject": subject, "data": {"from": was.get("state"), "to": now.get("state")}})
        if now.get("state") in ("accepted", "promoted", "card_suspect") and was.get("state") != now["state"]:
            entries.append({"kind": "outcome", "subject": subject, "data": {
                "result": now["state"], "assignment": now.get("assignment"), "attempts": now["attempts"],
                "form_retries": now["form_retries"], "tokens": now.get("tokens", 0), "cost": now.get("cost", "0")}})
    if before["phase"] != after["phase"]:
        entries.append({"kind": "phase", "subject": "", "data": {"from": before["phase"], "to": after["phase"]}})
    if before["budget"]["spent"] != after["budget"]["spent"]:
        entries.append({"kind": "budget", "subject": "", "data": {"spent": after["budget"]["spent"]}})
    return {"state": after, "evidence": list(evidence), "journal": entries}
