"""Финальные дети узла rptg.plan.route в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.plan.route.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import measure as _m_measure
from . import prior as _m_prior
from . import masks as _m_masks
from . import decide as _m_decide
from . import kind as _m_kind

if TYPE_CHECKING:
    from rptg._types import Assignment, Candidate, Candidates, Competence, Config, Json, Override, Strings
    from rptg.plan._types import KindDecisions, Ready
    from rptg.plan.route._types import Overrides, RouteCounts, RouteEnvJobs, RouteEnvs, RouteInfos, RouteMeasures



class measure:
    """Лист rptg.plan.route.measure: операции в обёртках условий."""

    @staticmethod
    def envs(state: Json, ready: Ready) -> RouteEnvJobs:
        """по готовым элементам, по порядку: у разложения не корня (роль designer) — все операции карточки узла, у функции — её операция; прочие не измеряются; окружение — все типы проекта по имени, переменные — параметры и result"""
        result = _m_measure.envs(state=state, ready=ready)
        return result

    @staticmethod
    def bind(state: Json, ready: Ready, envs: RouteEnvs) -> RouteMeasures:
        """те же операции в том же порядке: условия requires, затем ensures, и типы параметров, затем результат — каждое с окружением своей операции"""
        result = _m_measure.bind(state=state, ready=ready, envs=envs)
        return result


class prior:
    """Лист rptg.plan.route.prior: операции в обёртках условий."""

    @staticmethod
    def classes(state: Json, ready: Ready, infos: RouteInfos) -> Strings:
        """класс работы каждого готового элемента (LOGIC §6.3): карта и архитектор — map, сборка и разложение — design; функция — по первому признаку: эффекты — io, арифметика в ensures — compute, кванторы и агрегаты — search, строки в параметрах, результате или условиях — text, иначе transform; меры условий — по порядку заданий"""
        result = _m_prior.classes(state=state, ready=ready, infos=infos)
        _c.check('rptg.plan.route.prior:classes', 'ensures', [
            ('len(result) == len(ready)', lambda: (len(result) == len(ready))),
        ])
        return result

    @staticmethod
    def candidates(state: Json, ready: Ready, infos: RouteInfos, sizes: RouteCounts, manual: Overrides, classes: Strings, cfg: Config) -> Candidates:
        """кандидат на каждый готовый элемент с его классом: карта, разложение корня (архитектор) и сборки — оценка 0; разложение — S_раз по всем операциям узла; функция — S_исп; меры и размеры берутся по порядку заданий; est_lines заменяет ручное назначение"""
        _c.check('rptg.plan.route.prior:candidates', 'requires', [
            ('len(manual) == len(ready)', lambda: (len(manual) == len(ready))),
            ('len(classes) == len(ready)', lambda: (len(classes) == len(ready))),
        ])
        result = _m_prior.candidates(state=state, ready=ready, infos=infos, sizes=sizes, manual=manual, classes=classes, cfg=cfg)
        _c.check('rptg.plan.route.prior:candidates', 'ensures', [
            ('len(result) == len(ready)', lambda: (len(result) == len(ready))),
            ('forall c in result: c.prior >= 0 and c.prior <= 100', lambda: all(((c.prior >= 0) and (c.prior <= 100)) for c in result)),
        ])
        return result


class masks:
    """Лист rptg.plan.route.masks: операции в обёртках условий."""

    @staticmethod
    def resolve(subject: str, cfg: Config) -> Override:
        """узел — из предмета вид:узел[:операция] или сам путь; маски: точный путь, база.* — ровно один сегмент ниже базы, база.** — база и поддерево, level:a..b — уровни; точный путь сильнее маски с большим числом буквальных сегментов, та — уровня; при равенстве побеждает позднее; ключи сливаются, заданные поздним перекрывают"""
        result = _m_masks.resolve(subject=subject, cfg=cfg)
        return result


class decide:
    """Лист rptg.plan.route.decide: операции в обёртках условий."""

    @staticmethod
    def table(candidate: Candidate, manual: Override, table: Competence, cfg: Config) -> str:
        """оператор по таблице компетенций или пусто: у архитектора и при ручном операторе роли — пусто; клетки класса кандидата при G0, иначе сумма клеток оператора по всем классам (цена на успех — взвешенная по всем успехам клетки, подбор и проверка, «мало данных» — сумма выборки подбора и проверки меньше n_min: так определена клетка, bench К-4); годен оператор лестницы роли без пометки «мало данных» с долей успеха на подборе ≥ target и на проверке ≥ target − 0,1; берётся самый дешёвый на успех, при равенстве — ниже по лестнице"""
        result = _m_decide.table(candidate=candidate, manual=manual, table=table, cfg=cfg)
        return result

    @staticmethod
    def assign(candidate: Candidate, manual: Override, choice: str, cfg: Config) -> Assignment:
        """архитектор — ступень по правилу (start_rung, иначе первая), источник rule; ручной оператор роли из лестницы — его ступень, manual; выбор таблицы не пуст — его ступень, table; иначе ступень = 1 + число границ роли не выше прикидки, prior; ступень зажимается в start_rung..max_rung и длину лестницы"""
        result = _m_decide.assign(candidate=candidate, manual=manual, choice=choice, cfg=cfg)
        _c.check('rptg.plan.route.decide:assign', 'ensures', [
            ('result.subject == candidate.subject', lambda: (result.subject == candidate.subject)),
            ('result.role == candidate.role', lambda: (result.role == candidate.role)),
            ('result.class == candidate.class', lambda: (result.class_ == candidate.class_)),
            ('result.rung >= 1', lambda: (result.rung >= 1)),
        ])
        return result


class kind:
    """Лист rptg.plan.route.kind: операции в обёртках условий."""

    @staticmethod
    def children(state: Json, node: str) -> Strings:
        """дети разложения узла по порядку; пустой узел или узел без разложения — пусто"""
        result = _m_kind.children(state=state, node=node)
        return result

    @staticmethod
    def decide(state: Json, children: Strings, manual: Overrides, cfg: Config) -> KindDecisions:
        """по порядку правил, срабатывает первое: уровень = max_depth — final (2); есть uses — composite (3); операций больше final_max_ops — composite (4); функция узла повышена — composite (promotion); ручной kind — как назначено (5); est_lines (ручное или из карточки) больше final_max_lines × число операций — composite (6); иначе final (7)"""
        _c.check('rptg.plan.route.kind:decide', 'requires', [
            ('len(manual) == len(children)', lambda: (len(manual) == len(children))),
        ])
        result = _m_kind.decide(state=state, children=children, manual=manual, cfg=cfg)
        _c.check('rptg.plan.route.kind:decide', 'ensures', [
            ('len(result) == len(children)', lambda: (len(result) == len(children))),
        ])
        return result
