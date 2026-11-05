"""Лист rptg.plan.queue — очередь готовых элементов по фазе и состояниям (LOGIC §7.1).

Функции приняты по карточке design/rptg.plan.yaml; обвязку пишет скрипт. Состояние — JSON.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.plan._types import ReadyItem

if TYPE_CHECKING:
    from rptg._types import Config, Json
    from rptg.plan._types import Ready


def ready(state: Json, cfg: Config) -> Ready:
    """NEW и MAP — карта корня, после её приёмки разложение корня (архитектор); MAP_REVIEW, PAUSED,
    DONE — пусто; DESIGN — разложения по уровням сверху вниз, внутри уровня по пути; BUILD и E2E —
    разложения, затем функции по пути, затем сборки, чьи дети все приняты, снизу вверх. Элемент
    годен, если его состояние planned, writing, form_retry, repairing, escalated, stale или
    checking и он не ждёт пользователя."""
    phase, cards, elements, designs = state["phase"], state["cards"], state["elements"], state["designs"]
    good = {"planned", "writing", "form_retry", "repairing", "escalated", "stale", "checking"}
    root = next((c for c in cards if "." not in c), None) or next(iter(state["user_examples"]), ":").split(":")[0]

    def item(subject, role):
        kind, _, rest = subject.partition(":")
        node, _, op = rest.partition(":")
        return ReadyItem(subject=subject, kind=kind, role=role, level=node.count(".") + 1, node=node, op=op or None)

    def fit(subject):
        e = elements.get(subject)
        return e is None or e["state"] in good and not (e.get("policy_path") or "").startswith("user:")

    def accepted(subject):
        return elements.get(subject, {}).get("state") == "accepted"

    def built(node):
        return all(accepted(f"assembly:{k}") if k in designs else all(accepted(f"function:{k}:{o['name']}") for o in cards[k]["ops"])
                   for k in (c["id"] for c in designs[node]["children"]))

    def pick(prefix, role, order):
        return [item(s, role(s)) for s in sorted((s for s in elements if s.startswith(prefix) and fit(s)), key=order)]

    if phase in ("MAP_REVIEW", "PAUSED", "DONE"):
        return []
    if phase in ("NEW", "MAP"):
        first = f"design:{root}" if accepted(f"map:{root}") else f"map:{root}"
        return [item(first, "architect")] if fit(first) else []
    out = pick("design:", lambda s: "architect" if s == f"design:{root}" else "designer", lambda s: (s.count("."), s))
    if phase == "DESIGN":
        return out
    built_up = [r for r in pick("assembly:", lambda s: "designer", lambda s: (-s.count("."), s)) if built(r.node)]
    return out + pick("function:", lambda s: "implementer", lambda s: s) + built_up
