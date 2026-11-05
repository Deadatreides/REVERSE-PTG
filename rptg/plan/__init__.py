"""решения конвейера: очередь готовых задач, вид узла, класс работы, выбор оператора, машина состояний элементов, эскалация, раннее подозрение, повышение, остановки, бюджет

Сгенерировано tools/codegen0.py по design/rptg.plan.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Action, Assignment, Assignments, Candidate, Candidates, Competence, Config, Event, Evidences, State, Transition



def candidates(state: State, cfg: Config) -> Candidates:
    """готовые задачи в порядке очереди: в фазе DESIGN — разложения по уровням сверху вниз, в BUILD — функции и сборки снизу вверх"""
    result = _flows.candidates(state=state, cfg=cfg)
    _c.check('rptg.plan:candidates', 'ensures', [
        ('forall c in result: c.prior >= 0 and c.prior <= 100', lambda: all(((c.prior >= 0) and (c.prior <= 100)) for c in result)),
    ])
    return result


def assign(candidate: Candidate, table: Competence, cfg: Config) -> Assignment:
    """оператор для задачи: ручное назначение, иначе клетка таблицы компетенций, иначе априорная оценка и лестница"""
    result = _flows.assign(candidate=candidate, table=table, cfg=cfg)
    _c.check('rptg.plan:assign', 'ensures', [
        ('result.subject == candidate.subject', lambda: (result.subject == candidate.subject)),
        ('result.role == candidate.role', lambda: (result.role == candidate.role)),
        ('result.class == candidate.class', lambda: (result.class_ == candidate.class_)),
    ])
    return result


def pick(state: State, candidates: Candidates, assignments: Assignments, cfg: Config) -> Action:
    """выбрать действие: первая задача очереди с её назначением, утверждение, пауза по бюджету или конец"""
    _c.check('rptg.plan:pick', 'requires', [
        ('len(assignments) == len(candidates)', lambda: (len(assignments) == len(candidates))),
    ])
    result = _flows.pick(state=state, candidates=candidates, assignments=assignments, cfg=cfg)
    _c.check('rptg.plan:pick', 'ensures', [
        ('result.kind == "call_model" => result.task != null', lambda: ((not (result.kind == "call_model")) or (result.task is not None))),
        ('result.kind == "run_sandbox" => result.target != null and result.run != null', lambda: ((not (result.kind == "run_sandbox")) or ((result.target is not None) and (result.run is not None)))),
        ('result.kind == "ask_user" => result.question != null', lambda: ((not (result.kind == "ask_user")) or (result.question is not None))),
        ('state.phase == "DONE" => result.kind == "stop"', lambda: ((not (state.phase == "DONE")) or (result.kind == "stop"))),
        ('state.phase == "MAP_REVIEW" => result.kind == "ask_user"', lambda: ((not (state.phase == "MAP_REVIEW")) or (result.kind == "ask_user"))),
    ])
    return result


def transition(state: State, event: Event, evidence: Evidences, cfg: Config) -> Transition:
    """событие и его доказательства → состояния элементов (LOGIC §7.2–§7.8), фаза проекта, бюджет, журнал"""
    _c.check('rptg.plan:transition', 'requires', [
        ('event.kind == "model_answered" => event.task != null and event.answer != null', lambda: ((not (event.kind == "model_answered")) or ((event.task is not None) and (event.answer is not None)))),
        ('event.kind == "sandbox_finished" => event.target != null and event.output != null', lambda: ((not (event.kind == "sandbox_finished")) or ((event.target is not None) and (event.output is not None)))),
        ('forall e in evidence: e.hard', lambda: all(e.hard for e in evidence)),
    ])
    result = _flows.transition(state=state, event=event, evidence=evidence, cfg=cfg)
    _c.check('rptg.plan:transition', 'ensures', [
        ('len(result.journal) >= 1', lambda: (len(result.journal) >= 1)),
        ('forall e in result.evidence: e.hard', lambda: all(e.hard for e in result.evidence)),
    ])
    return result
