"""Лист rptg.views.node — представление узла: карточка, разложение, элементы (ARCHITECTURE §7, §8).

Функции приняты по карточке design/rptg.views.yaml; обвязку пишет скрипт. Приёмку элементов — каких
слоёв не хватает — даёт check:accepted отображением в схеме.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json, ViewQuery
    from rptg.views._types import NodeAcceptances, NodeSubjects


def subjects(state: Json, query: ViewQuery) -> NodeSubjects:
    """Предметы элементов узла запроса (map, design, function, assembly этого узла) по порядку предметов."""
    return sorted(k for k in state["elements"] if k.split(":")[1] == query.subject)


def view(state: Json, query: ViewQuery, subjects: NodeSubjects, acceptances: NodeAcceptances) -> Json:
    """Узел запроса: карточка или null, разложение (дети и операции схем) или null, элементы по порядку
    предметов — состояние, оператор, ступень и источник назначения (нет — пустые), попытки, повторы
    формы, токены, цена, отчёты, причина ожидания пользователя (нет — пусто), принят ли и каких слоёв не
    хватает."""
    node, design = query.subject, state["designs"].get(query.subject)

    def element(subject, acc):
        e = state["elements"][subject]
        a, path = e.get("assignment") or {}, e.get("policy_path") or ""
        return {"subject": subject, "state": e["state"], "operator": a.get("operator", ""), "rung": a.get("rung", 0),
                "decided_by": a.get("decided_by", ""), "attempts": e["attempts"], "form_retries": e["form_retries"],
                "tokens": e.get("tokens", 0), "cost": e.get("cost", "0"), "reports": e["reports"],
                "waiting": path.split(":")[1] if path.startswith("user:") else "", "accepted": acc.accepted, "missing": list(acc.missing)}

    shape = {"children": [c["id"] for c in design["children"]], "flows": list(design["flows"])} if design else None
    return {"node": node, "card": state["cards"].get(node), "design": shape,
            "elements": [element(s, a) for s, a in zip(subjects, acceptances)]}
