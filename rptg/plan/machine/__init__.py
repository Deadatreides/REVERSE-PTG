"""машина состояний элементов (LOGIC §7.2–§7.8): доказательства и ответ в состояние, наблюдаемые, пошаговое исполнение политики arch2, утверждения, маршрутизация детей, подозрение и ревизия владельцем, повышение, устаревание и перепроверка без модели, мёртвые операции, остановки, фаза, бюджет, журнал

Сгенерировано tools/codegen0.py по design/rptg.plan.machine.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Answer, Assignments, Config, Event, Evidences, State, Transition
    from rptg.plan._types import Absorbed, KindDecisions, Policies, PolicyStep, Settled



def absorb(state: State, event: Event, evidence: Evidences, answer: Answer, cfg: Config) -> Absorbed:
    """впитать событие: доказательства и расход в состояние, ответ модели — если он чист, наблюдаемые, шаг политики, элемент; ответ пользователя и команда — утверждение, решение, перепроверка, пауза, бюджет"""
    _c.check('rptg.plan.machine:absorb', 'requires', [
        ('forall e in evidence: e.hard', lambda: all(e.hard for e in evidence)),
    ])
    result = _flows.absorb(state=state, event=event, evidence=evidence, answer=answer, cfg=cfg)
    return result


def settle(before: State, absorbed: Absorbed, kinds: KindDecisions, cfg: Config) -> Settled:
    """следствия шага: принятое разложение — дети по видам, сборка узла, версии; карта — задача разложения корня; подозрение — владельцу на ревизию или пользователю; повышение листа; ревизия — оставить или изменить, изменившиеся карточки, колебание; вина в Э6 — переоткрыть виновного"""
    result = _flows.settle(before=before, absorbed=absorbed, kinds=kinds, cfg=cfg)
    return result


def recheck(settled: Settled, cfg: Config) -> Settled:
    """мёртвые операции, когда всё дерево разложено (LOGIC §7.6); устаревание изменившегося (§7.7): непринятое без сохранённой версии начинается заново на новой карточке, сохранённое — перепроверка без модели: карта, разложения и статика функций заново через check, прогоны — позже в песочнице; ждущее утверждения не перепроверяется"""
    result = _flows.recheck(settled=settled, cfg=cfg)
    return result


def close(before: State, absorbed: Absorbed, settled: Settled, evidence: Evidences, cfg: Config) -> Transition:
    """фаза проекта по состояниям элементов и остановкам (LOGIC §7.1, §7.8), затем итог перехода: состояние, доказательства события, журнал — доказательства, изменившиеся элементы, фаза, бюджет, записи следствий"""
    _c.check('rptg.plan.machine:close', 'requires', [
        ('forall e in evidence: e.hard', lambda: all(e.hard for e in evidence)),
    ])
    result = _flows.close(before=before, absorbed=absorbed, settled=settled, evidence=evidence, cfg=cfg)
    _c.check('rptg.plan.machine:close', 'ensures', [
        ('len(result.journal) >= 1', lambda: (len(result.journal) >= 1)),
        ('forall e in result.evidence: e.hard', lambda: all(e.hard for e in result.evidence)),
    ])
    return result


def policies(cfg: Config) -> Policies:
    """деревья политики по ролям: своя политика роли из cfg.policies после валидатора, иначе политика по умолчанию LOGIC §7.3 из repair.per_rung, repair.form_retries и лестницы роли; дерево лишнего круга"""
    result = _flows.policies(cfg=cfg)
    return result


def dispatch(state: State, subject: str, assignments: Assignments, cfg: Config) -> PolicyStep:
    """позиция элемента → ближайший вызов модели по наблюдаемым самого элемента (без нового события): оператор и ступень, формулировка, нужен ли отчёт; у элемента без назначения — назначение кандидата (список из одного или пуст)"""
    result = _flows.dispatch(state=state, subject=subject, assignments=assignments, cfg=cfg)
    return result
