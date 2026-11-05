"""маршрутизация (LOGIC §6): вид ребёнка, класс работы, априорная оценка, ручные назначения по маскам, таблица компетенций с гейтом G0, лестница

Сгенерировано tools/codegen0.py по design/rptg.plan.route.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Assignment, Candidate, Candidates, Competence, Config, Json, Override
    from rptg.plan._types import KindDecisions, Ready



def score(state: Json, ready: Ready, cfg: Config) -> Candidates:
    """готовые элементы → кандидаты: класс по LOGIC §6.3, прикидка S_раз или S_исп по §6.5 на мерах условий и размерах типов в окружении каждой операции; карта, разложение корня и сборки — оценка 0"""
    result = _flows.score(state=state, ready=ready, cfg=cfg)
    _c.check('rptg.plan.route:score', 'ensures', [
        ('len(result) == len(ready)', lambda: (len(result) == len(ready))),
        ('forall c in result: c.prior >= 0 and c.prior <= 100', lambda: all(((c.prior >= 0) and (c.prior <= 100)) for c in result)),
    ])
    return result


def assign(candidate: Candidate, table: Competence, cfg: Config) -> Assignment:
    """оператор задачи: ручное назначение роли по маскам, иначе клетка таблицы (гейт G0), иначе ступень по прикидке; start_rung и max_rung ограничивают ступень; архитектор — первая ступень по правилу"""
    result = _flows.assign(candidate=candidate, table=table, cfg=cfg)
    _c.check('rptg.plan.route:assign', 'ensures', [
        ('result.subject == candidate.subject', lambda: (result.subject == candidate.subject)),
        ('result.role == candidate.role', lambda: (result.role == candidate.role)),
        ('result.class == candidate.class', lambda: (result.class_ == candidate.class_)),
    ])
    return result


def fallback(candidate: Candidate, cfg: Config) -> Assignment:
    """назначение без таблицы компетенций: правило архитектора, ручное назначение роли, иначе ступень по прикидке — чтобы восстановить назначение элемента по ответу модели, когда таблицы в переходе нет"""
    result = _flows.fallback(candidate=candidate, cfg=cfg)
    _c.check('rptg.plan.route:fallback', 'ensures', [
        ('result.subject == candidate.subject', lambda: (result.subject == candidate.subject)),
        ('result.role == candidate.role', lambda: (result.role == candidate.role)),
    ])
    return result


def kinds(state: Json, node: str, cfg: Config) -> KindDecisions:
    """виды детей разложения узла по правилам LOGIC §6.2 и повышению (§7.4); пустой узел или узел без разложения — пусто"""
    result = _flows.kinds(state=state, node=node, cfg=cfg)
    return result


def override(subject: str, cfg: Config) -> Override:
    """ручные назначения узла по маскам project.yaml; узел — из предмета вид:узел[:операция] или сам путь узла, уровень — глубина узла; точный путь сильнее маски с большим числом буквальных сегментов, та — уровня, при равенстве побеждает позднее (LOGIC §6.6)"""
    result = _flows.override(subject=subject, cfg=cfg)
    return result
