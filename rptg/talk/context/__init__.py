"""факты задачи из состояния по правилу контекста LOGIC §8.1 и контекст починки: только перечисленное для вида задачи, без прежнего ответа

Сгенерировано tools/codegen0.py по design/rptg.talk.context.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Json, Task
    from rptg.talk._types import Facts



def facts(task: Task, state: Json, cfg: Json) -> Facts:
    """карта — замысел и приёмочные примеры; разложение X — карточка X, путь от корня строкой «id — назначение» на предка, раздел карты ветви (у корня — вся карта; раздел — заголовок с {#имя} уровня 2 до заголовка того же или старшего уровня), интерфейсы uses без примеров, типы владельцев-предков и самого X по имени, пределы с уровнем X; ревизия — ещё текущее разложение X и отчёты элементов поддерева X; шаги split — как разложение; функция — карточка операции, назначение узла, её типы с замыканием по ссылкам, импорты и эффекты узла, предел сложности и договор Э1, если объявлен; у задачи с отчётом — первым разделом отчёт"""
    result = _flows.facts(task=task, state=state, cfg=cfg)
    _c.check('rptg.talk.context:facts', 'ensures', [
        ('task.kind == "map" => forall s in result.sections: s.key in {"idea", "examples", "report"}', lambda: ((not (task.kind == "map")) or all((s.key in ("idea", "examples", "report",)) for s in result.sections))),
        ('task.kind == "function" => forall s in result.sections: s.key in {"op", "purpose", "types", "imports", "limits", "report"}', lambda: ((not (task.kind == "function")) or all((s.key in ("op", "purpose", "types", "imports", "limits", "report",)) for s in result.sections))),
        ('task.kind != "revision" => forall s in result.sections: s.key != "design" and s.key != "below"', lambda: ((not (task.kind != "revision")) or all(((s.key != "design") and (s.key != "below")) for s in result.sections))),
        ('task.report != null => exists s in result.sections: s.key == "report"', lambda: ((not (task.report is not None)) or any((s.key == "report") for s in result.sections))),
        ('task.report == null => forall s in result.sections: s.key != "report"', lambda: ((not (task.report is None)) or all((s.key != "report") for s in result.sections))),
    ])
    return result
