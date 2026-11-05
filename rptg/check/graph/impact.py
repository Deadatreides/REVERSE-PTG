"""Лист rptg.check.graph.impact — устаревание после смены карточек узлов (LOGIC §7.7).

Функции приняты по карточке design/rptg.check.graph.yaml; обвязку пишет скрипт. Устаревшее
перепроверяется: если проверки проходят на новых хэшах, элемент принят снова без вызова модели.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json, Strings


def stale(state: Json, changed: Strings) -> Strings:
    """Для каждого изменённого узла X: разложения, чьи схемы вызывают X (родитель и узлы с X в
    uses), разложение X против нового интерфейса, функции X, если он финальный; затем сборки X, всех
    предков и каждого устаревшего разложения с его предками. Независимые ветви не устаревают."""
    cards, designs = state["cards"], state["designs"]

    def calls(node, target):
        pool = {u.rsplit(".", 1)[-1]: u for u in cards[node]["uses"]}
        pool.update({c["id"].rsplit(".", 1)[-1]: c["id"] for c in designs[node]["children"]})
        refs = [n.get("call", n.get("map", n.get("fold", ""))) for f in designs[node]["flows"].values() for n in f["nodes"]]
        return any(pool.get(r.split(":")[0]) == target for r in refs)

    def of_node(x):
        own = {f"design:{x}"} if x in designs else {f"function:{x}:{o['name']}" for o in cards[x]["ops"]}
        return own | {f"design:{d}" for d in designs if d != x and calls(d, x)}

    def assemblies(node):
        parts = node.split(".")
        return {f"assembly:{a}" for a in (".".join(parts[:i]) for i in range(1, len(parts) + 1)) if a in designs}

    out = {s for x in changed if x in cards for s in of_node(x)}
    roots = [s.partition(":")[2] for s in out if s.startswith("design:")] + list(changed)
    return sorted(out | {a for node in roots for a in assemblies(node)})
