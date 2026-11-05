"""Финальные дети узла rptg.talk.context в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.talk.context.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import idea as _m_idea
from . import branch as _m_branch
from . import leaf as _m_leaf
from . import repair as _m_repair
from . import merge as _m_merge

if TYPE_CHECKING:
    from rptg._types import Json, Task
    from rptg.talk._types import Facts



class idea:
    """Лист rptg.talk.context.idea: операции в обёртках условий."""

    @staticmethod
    def facts(task: Task, state: Json) -> Facts:
        """карта — разделы idea (замысел) и examples (примеры пользователя по операциям); другой вид задачи — пусто"""
        result = _m_idea.facts(task=task, state=state)
        _c.check('rptg.talk.context.idea:facts', 'ensures', [
            ('task.kind != "map" => len(result.sections) == 0', lambda: ((not (task.kind != "map")) or (len(result.sections) == 0))),
            ('forall s in result.sections: s.key in {"idea", "examples"}', lambda: all((s.key in ("idea", "examples",)) for s in result.sections)),
        ])
        return result


class branch:
    """Лист rptg.talk.context.branch: операции в обёртках условий."""

    @staticmethod
    def facts(task: Task, state: Json, cfg: Json) -> Facts:
        """разложение, ревизия и шаги split — разделы card (карточка X), path (строки «id — назначение» строгих предков от корня), map (у корня — вся карта; иначе раздел с заголовком, где есть {#имя} узла уровня 2 ветви, до заголовка того же или старшего уровня; нет — пустая строка), uses (карточки uses: id и операции без примеров), types (типы, чей владелец — X или его предок, по имени), limits (уровень X, max_depth, max_children, final_max_ops, k_lists); ревизия — ещё design (текущее разложение X) и below (предмет и отчёты элементов строго под X с отчётами, по предмету); другой вид — пусто"""
        result = _m_branch.facts(task=task, state=state, cfg=cfg)
        _c.check('rptg.talk.context.branch:facts', 'ensures', [
            ('task.kind == "map" or task.kind == "function" => len(result.sections) == 0', lambda: ((not ((task.kind == "map") or (task.kind == "function"))) or (len(result.sections) == 0))),
            ('forall s in result.sections: s.key in {"card", "path", "map", "uses", "types", "limits", "design", "below"}', lambda: all((s.key in ("card", "path", "map", "uses", "types", "limits", "design", "below",)) for s in result.sections)),
            ('task.kind != "revision" => forall s in result.sections: s.key != "design" and s.key != "below"', lambda: ((not (task.kind != "revision")) or all(((s.key != "design") and (s.key != "below")) for s in result.sections))),
        ])
        return result


class leaf:
    """Лист rptg.talk.context.leaf: операции в обёртках условий."""

    @staticmethod
    def facts(task: Task, state: Json, cfg: Json) -> Facts:
        """функция — разделы op (карточка операции из предмета, с примерами), purpose (назначение узла), types (типы проекта из параметров и результата, запись [T] — тип T, с замыканием по ссылкам $ref внутри схем, по имени), imports (allowed_imports и effects узла), limits (max_complexity проекта и договор Э1 операции, если объявлен); другой вид — пусто"""
        result = _m_leaf.facts(task=task, state=state, cfg=cfg)
        _c.check('rptg.talk.context.leaf:facts', 'ensures', [
            ('task.kind != "function" => len(result.sections) == 0', lambda: ((not (task.kind != "function")) or (len(result.sections) == 0))),
            ('forall s in result.sections: s.key in {"op", "purpose", "types", "imports", "limits"}', lambda: all((s.key in ("op", "purpose", "types", "imports", "limits",)) for s in result.sections)),
        ])
        return result


class repair:
    """Лист rptg.talk.context.repair: операции в обёртках условий."""

    @staticmethod
    def facts(task: Json) -> Facts:
        """у задачи есть отчёт — раздел report с ним как есть; нет — пусто. Задача приходит в JSON: отчёт уже записан так, как его покажет подсказка (LOGIC §8.4)"""
        result = _m_repair.facts(task=task)
        _c.check('rptg.talk.context.repair:facts', 'ensures', [
            ('len(result.sections) <= 1', lambda: (len(result.sections) <= 1)),
            ('forall s in result.sections: s.key == "report"', lambda: all((s.key == "report") for s in result.sections)),
        ])
        return result


class merge:
    """Лист rptg.talk.context.merge: операции в обёртках условий."""

    @staticmethod
    def facts(idea: Facts, branch: Facts, leaf: Facts, repair: Facts) -> Facts:
        """разделы отчёта, затем карты, разложения и функции — подряд; из трёх последних на деле непуст один. Отчёт первым: полнота нахождения у малых моделей падает с позицией монотонно (K1)"""
        result = _m_merge.facts(idea=idea, branch=branch, leaf=leaf, repair=repair)
        _c.check('rptg.talk.context.merge:facts', 'ensures', [
            ('len(result.sections) == len(idea.sections) + len(branch.sections) + len(leaf.sections) + len(repair.sections)', lambda: (len(result.sections) == (((len(idea.sections) + len(branch.sections)) + len(leaf.sections)) + len(repair.sections)))),
        ])
        return result
