"""Лист rptg.check.graph.reach — достижимость операций от операций корня (LOGIC §3 I10, §7.6).

Функции приняты по карточке design/rptg.check.graph.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json, Strings


def dead_ops(state: Json) -> Strings:
    """Операции всех карточек, до которых не доходит ни один вызов от операций корня, по порядку.
    Корень — карточка без родителя; дерева ещё нет — пусто. Вызов идёт по схеме составного узла;
    короткое имя — среди детей разложения, потом среди uses узла (§2.3); без имени операции —
    единственная операция вызываемого."""
    cards, designs = state["cards"], state["designs"]
    roots = [c for c in cards.values() if not c.get("parent")]

    def called(node, n):
        pool = {u.rsplit(".", 1)[-1]: u for u in cards[node]["uses"]}
        pool.update({c["id"].rsplit(".", 1)[-1]: c["id"] for c in designs[node]["children"]})
        short, _, name = n.get("call", n.get("map", n.get("fold", ""))).partition(":")
        target = pool.get(short, "")
        return f"{target}:{name or cards[target]['ops'][0]['name']}" if target in cards else None

    def walk(todo):
        seen = set()
        while todo:
            ref = todo.pop()
            node, _, name = ref.partition(":")
            if ref not in seen and node in designs:
                todo += [r for n in designs[node]["flows"].get(name, {"nodes": []})["nodes"] if (r := called(node, n))]
            seen.add(ref)
        return seen

    if len(roots) != 1:
        return []
    seen = walk([f"{roots[0]['id']}:{o['name']}" for o in roots[0]["ops"]])
    return sorted(f"{c['id']}:{o['name']}" for c in cards.values() for o in c["ops"] if f"{c['id']}:{o['name']}" not in seen)
