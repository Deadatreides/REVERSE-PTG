"""Финальные дети узла rptg.plan.choose в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.plan.choose.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import pending as _m_pending

if TYPE_CHECKING:
    from rptg._types import Action, Assignments, Candidates, Config, Json, Sha
    from rptg.plan._types import Policies, PolicyStep
    from rptg.plan.choose._types import Choice



class pending:
    """Лист rptg.plan.choose.pending: операции в обёртках условий."""

    @staticmethod
    def choose(state: Json, candidates: Candidates, assignments: Assignments, policies: Policies, cfg: Config) -> Choice:
        """по порядку: DONE — stop; PAUSED — первый элемент, ждущий пользователя (ask), иначе pause; routing.adapt или explore > 0 — pause (вне этой постройки); у политик нарушения — pause с ними; MAP_REVIEW — approve разложения корня; бюджет исчерпан — pause; есть кандидат — первый: сборка — sandbox (корень — program и smoke, иначе node_package и e6), функция на проверке — sandbox по недостающему на текущем хэше (нет Э1 от mypy — e1_mypy, иначе e2_e3), прочее — model с назначением кандидата; иначе разложение на утверждении — approve; элемент ждёт пользователя — ask; иначе pause «нет готовых задач»"""
        _c.check('rptg.plan.choose.pending:choose', 'requires', [
            ('len(assignments) == len(candidates)', lambda: (len(assignments) == len(candidates))),
        ])
        result = _m_pending.choose(state=state, candidates=candidates, assignments=assignments, policies=policies, cfg=cfg)
        _c.check('rptg.plan.choose.pending:choose', 'ensures', [
            ('len(result.assignments) <= 1', lambda: (len(result.assignments) <= 1)),
        ])
        return result

    @staticmethod
    def action(state: Json, choice: Choice, step: PolicyStep, hash: Sha) -> Action:
        """stop, pause — действие с причиной (у stop без причины); approve — ask_user {approve: узел, design_hash}; ask — ask_user с вопросом выбора; sandbox — run_sandbox с целью и прогоном; model — шаг ждёт вызова: задача (вид: map, design, revision — есть версия разложения узла, function), роль, оператор и формулировка шага, попытка = попытки элемента + 1, у alternative — без прибавки, отчёт — первый отчёт элемента, если шаг его просит; шаг не ждёт вызова — pause с причиной"""
        result = _m_pending.action(state=state, choice=choice, step=step, hash=hash)
        _c.check('rptg.plan.choose.pending:action', 'ensures', [
            ('result.kind == "call_model" => result.task != null', lambda: ((not (result.kind == "call_model")) or (result.task is not None))),
            ('result.kind == "run_sandbox" => result.target != null and result.run != null', lambda: ((not (result.kind == "run_sandbox")) or ((result.target is not None) and (result.run is not None)))),
            ('result.kind == "ask_user" => result.question != null', lambda: ((not (result.kind == "ask_user")) or (result.question is not None))),
        ])
        return result
