"""выбор действия: конец, пауза, вопрос утверждения или решения, вызов модели или прогон песочницы для первого готового элемента

Сгенерировано tools/codegen0.py по design/rptg.plan.choose.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Action, Assignments, Candidates, Config, State



def action(state: State, candidates: Candidates, assignments: Assignments, cfg: Config) -> Action:
    """DONE — stop; PAUSED — pause; маршрутизация вне постройки (adapt, explore) или политика с нарушениями — pause с причиной; бюджет исчерпан — pause; MAP_REVIEW — вопрос утверждения корня с дайджестом разложения; иначе первый кандидат: функция на проверке — прогон песочницы, сборка — прогон e6 или smoke у корня, прочее — вызов модели по шагу политики; кандидатов нет — вопрос, который ждёт пользователя, иначе пауза"""
    _c.check('rptg.plan.choose:action', 'requires', [
        ('len(assignments) == len(candidates)', lambda: (len(assignments) == len(candidates))),
    ])
    result = _flows.action(state=state, candidates=candidates, assignments=assignments, cfg=cfg)
    _c.check('rptg.plan.choose:action', 'ensures', [
        ('result.kind == "call_model" => result.task != null', lambda: ((not (result.kind == "call_model")) or (result.task is not None))),
        ('result.kind == "run_sandbox" => result.target != null and result.run != null', lambda: ((not (result.kind == "run_sandbox")) or ((result.target is not None) and (result.run is not None)))),
        ('result.kind == "ask_user" => result.question != null', lambda: ((not (result.kind == "ask_user")) or (result.question is not None))),
        ('state.phase == "DONE" => result.kind == "stop"', lambda: ((not (state.phase == "DONE")) or (result.kind == "stop"))),
        ('state.phase == "MAP_REVIEW" => result.kind == "ask_user"', lambda: ((not (state.phase == "MAP_REVIEW")) or (result.kind == "ask_user"))),
    ])
    return result
