"""Лист rptg.talk.context.branch — факты задачи разложения узла X (LOGIC §8.1, §7.5).

Функции приняты по карточке design/rptg.talk.context.yaml; обвязку пишет скрипт. Конструктор видит
свою ветвь и только её: карточку X, путь от корня, раздел карты, интерфейсы uses, видимые типы.
Чужих поддеревьев нет (F35). Прежнего ответа нет и у ревизии: её «текущее разложение» — принятое.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.talk._types import Fact, Facts

if TYPE_CHECKING:
    from rptg._types import Json, Task


def facts(task: Task, state: Json, cfg: Json) -> Facts:
    """Разложение, ревизия и шаги split — card, path, map, uses, types, limits; у ревизии ещё design и
    below. Раздел карты: у корня — вся карта; иначе заголовок с {#имя} узла уровня 2 ветви до
    заголовка того же или старшего уровня; нет — пустая строка. Другой вид — пусто."""
    if task.kind in ("map", "function"):
        return Facts(sections=[])
    x = task.subject.split(":")[1]
    parts = x.split(".")
    card, limits = state["cards"][x], cfg["limits"]

    def level(line):
        return len(line) - len(line.lstrip("#")) if line.startswith("#") else 0

    def section(text):
        if len(parts) == 1:
            return text
        lines = text.split("\n")
        start = next((i for i, line in enumerate(lines) if level(line) and "{#" + parts[1] + "}" in line), None)
        if start is None:
            return ""
        end = next((j for j in range(start + 1, len(lines)) if 0 < level(lines[j]) <= level(lines[start])), len(lines))
        return "\n".join(lines[start:end]).strip()

    def interfaces():
        return [{"id": u, "ops": [{k: v for k, v in op.items() if k != "examples"} for op in state["cards"][u]["ops"]]}
                for u in card["uses"]]

    def reports_below():
        return [{"subject": s, "reports": e["reports"]} for s, e in sorted(state["elements"].items())
                if s.split(":")[1].startswith(x + ".") and e["reports"]]

    owners = {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    sections = [
        Fact(key="card", value=card),
        Fact(key="path", value=[f"{a} — {state['cards'][a]['purpose']}" for a in sorted(owners - {x}, key=len)]),
        Fact(key="map", value=section(state["map_text"])),
        Fact(key="uses", value=interfaces()),
        Fact(key="types", value=[state["types"][n] for n in sorted(state["types"]) if state["types"][n]["owner"] in owners]),
        Fact(key="limits", value={"level": len(parts), "max_depth": limits["max_depth"], "max_children": limits["max_children"],
                                  "final_max_ops": limits["final_max_ops"], "k_lists": limits["k_lists"]}),
    ]
    if task.kind == "revision":
        sections += [Fact(key="design", value=state["designs"][x]), Fact(key="below", value=reports_below())]
    return Facts(sections=sections)
