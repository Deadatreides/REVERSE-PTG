"""функциональное ядро rptg: по состоянию проекта решает, что делать дальше, проверяет ответы моделей и прогоны, строит файлы программы; ввод-вывод, часы и цикл — в оболочке

Сгенерировано tools/codegen0.py по design/rptg.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Action, BuildTarget, CalibrationPlan, CalibrationResults, Competence, Config, ControlCases, Event, FileSet, Json, ProviderRequest, RawAnswer, ReferenceSet, SelftestReport, State, Strings, Task, Transition, View, ViewQuery



def plan_next(state: State, cfg: Config, table: Competence) -> Action:
    """следующее действие: вызвать модель, прогнать песочницу, спросить пользователя, пауза или конец"""
    result = _flows.plan_next(state=state, cfg=cfg, table=table)
    _c.check('rptg:plan_next', 'ensures', [
        ('result.kind == "call_model" => result.task != null', lambda: ((not (result.kind == "call_model")) or (result.task is not None))),
        ('result.kind == "run_sandbox" => result.target != null and result.run != null', lambda: ((not (result.kind == "run_sandbox")) or ((result.target is not None) and (result.run is not None)))),
        ('result.kind == "ask_user" => result.question != null', lambda: ((not (result.kind == "ask_user")) or (result.question is not None))),
        ('state.phase == "DONE" => result.kind == "stop"', lambda: ((not (state.phase == "DONE")) or (result.kind == "stop"))),
        ('state.phase == "MAP_REVIEW" => result.kind == "ask_user"', lambda: ((not (state.phase == "MAP_REVIEW")) or (result.kind == "ask_user"))),
    ])
    return result


def apply_event(state: State, event: Event, cfg: Config) -> Transition:
    """событие → проверки, новое состояние, записи журнала; ответ модели проверяется здесь, модель его не оценивает"""
    _c.check('rptg:apply_event', 'requires', [
        ('event.kind == "model_answered" => event.task != null and event.answer != null', lambda: ((not (event.kind == "model_answered")) or ((event.task is not None) and (event.answer is not None)))),
        ('event.kind == "sandbox_finished" => event.target != null and event.output != null', lambda: ((not (event.kind == "sandbox_finished")) or ((event.target is not None) and (event.output is not None)))),
    ])
    result = _flows.apply_event(state=state, event=event, cfg=cfg)
    _c.check('rptg:apply_event', 'ensures', [
        ('len(result.journal) >= 1', lambda: (len(result.journal) >= 1)),
        ('forall e in result.evidence: e.hard', lambda: all(e.hard for e in result.evidence)),
    ])
    return result


def render_call(task: Task, state: State, cfg: Config) -> ProviderRequest:
    """задача → запрос поставщику: подсказка с устойчивым префиксом, способ вывода оператора; ключей в запросе нет"""
    _c.check('rptg:render_call', 'requires', [
        ('task.operator in cfg.operators', lambda: (task.operator in cfg.operators)),
    ])
    result = _flows.render_call(task=task, state=state, cfg=cfg)
    _c.check('rptg:render_call', 'ensures', [
        ('result.operator == task.operator', lambda: (result.operator == task.operator)),
    ])
    return result


def read_answer(provider: str, raw: Json) -> RawAnswer:
    """сырой ответ поставщика → текст, токены, причина остановки, отказ; разбирается конверт, а не содержимое"""
    _c.check('rptg:read_answer', 'requires', [
        ('provider in {"anthropic", "openai", "google", "openrouter", "openai_compatible", "llamacpp"}', lambda: (provider in ("anthropic", "openai", "google", "openrouter", "openai_compatible", "llamacpp",))),
    ])
    result = _flows.read_answer(provider=provider, raw=raw)
    _c.check('rptg:read_answer', 'ensures', [
        ('result.input_tokens >= 0 and result.output_tokens >= 0', lambda: ((result.input_tokens >= 0) and (result.output_tokens >= 0))),
        ('result.refusal => result.finish_reason == "refusal"', lambda: ((not result.refusal) or (result.finish_reason == "refusal"))),
    ])
    return result


def build_files(state: State, target: BuildTarget, cfg: Config) -> FileSet:
    """файлы для песочницы или готовой программы: тесты функции (Э2, Э3), пакет составного узла (Э6), вся программа"""
    _c.check('rptg:build_files', 'requires', [
        ('target.kind == "function_tests" => target.subject in state.code', lambda: ((not (target.kind == "function_tests")) or (target.subject in state.code))),
    ])
    result = _flows.build_files(state=state, target=target, cfg=cfg)
    _c.check('rptg:build_files', 'ensures', [
        ('len(result.files) >= 1', lambda: (len(result.files) >= 1)),
    ])
    return result


def calibration_plan(reference: ReferenceSet, operators: Strings, cfg: Config) -> CalibrationPlan:
    """эталонный набор и операторы → раздел на подбор и проверку по роду, внутри рода — по хэшу имени, чтобы каждый род делился поровну, и задачи: каждый оператор на каждой задаче"""
    _c.check('rptg:calibration_plan', 'requires', [
        ('len(reference.items) >= 2', lambda: (len(reference.items) >= 2)),
        ('len(operators) >= 1', lambda: (len(operators) >= 1)),
    ])
    result = _flows.calibration_plan(reference=reference, operators=operators, cfg=cfg)
    _c.check('rptg:calibration_plan', 'ensures', [
        ('len(result.tasks) == len(reference.items) * len(operators)', lambda: (len(result.tasks) == (len(reference.items) * len(operators)))),
        ('len(result.fit) + len(result.check) == len(reference.items)', lambda: ((len(result.fit) + len(result.check)) == len(reference.items))),
        ('forall i in result.fit: not (i in result.check)', lambda: all((not (i in result.check)) for i in result.fit)),
    ])
    return result


def competence(results: CalibrationResults, plan: CalibrationPlan, cfg: Config) -> Competence:
    """итоги калибровки → таблица: успех по оператору и классу на подборе и проверке, цена на успех, гейт G0"""
    result = _flows.competence(results=results, plan=plan, cfg=cfg)
    _c.check('rptg:competence', 'ensures', [
        ('forall c in result.cells: c.ok_fit <= c.n_fit and c.ok_check <= c.n_check', lambda: all(((c.ok_fit <= c.n_fit) and (c.ok_check <= c.n_check)) for c in result.cells)),
        ('forall c in result.cells: c.low_data == (c.n_fit + c.n_check < cfg.routing.n_min)', lambda: all((c.low_data == ((c.n_fit + c.n_check) < cfg.routing.n_min)) for c in result.cells)),
    ])
    return result


def selftest(cases: ControlCases, cfg: Config) -> SelftestReport:
    """контрольные случаи всех проверок → по каждой проверке: сколько сошлось и доверенная ли она"""
    _c.check('rptg:selftest', 'requires', [
        ('len(cases) >= 1', lambda: (len(cases) >= 1)),
    ])
    result = _flows.selftest(cases=cases, cfg=cfg)
    _c.check('rptg:selftest', 'ensures', [
        ('forall r in result.checks: r.trusted == (r.failed == 0)', lambda: all((r.trusted == (r.failed == 0)) for r in result.checks)),
        ('forall r in result.checks: r.passed + r.failed >= 1', lambda: all(((r.passed + r.failed) >= 1) for r in result.checks)),
    ])
    return result


def view(state: State, query: ViewQuery, cfg: Config) -> View:
    """представление состояния для окна и командной строки"""
    result = _flows.view(state=state, query=query, cfg=cfg)
    _c.check('rptg:view', 'ensures', [
        ('result.kind == query.kind', lambda: (result.kind == query.kind)),
    ])
    return result
