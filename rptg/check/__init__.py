"""проверки П1–П5, П7, Э1 и толкование прогонов Э2, Э3, Э6: извлечение ответа, форма, структура графа, данные, условия, примеры, статика кода, распределение вины; приёмка по хэшам, отчёт о нарушении, мёртвые операции, устаревание, контрольные случаи

Сгенерировано tools/codegen0.py по design/rptg.check.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Acceptance, Answer, CaseResult, CaseResults, Config, ControlCase, Event, Evidence, Evidences, Report, SelftestReport, State, Strings, Subject



def evaluate(state: State, event: Event, cfg: Config) -> Evidences:
    """проверки, которых требует событие, в порядке P1 P2 P3 P4 P5 P7 E1 E2 E3 E6; неприменимые не выполняются"""
    _c.check('rptg.check:evaluate', 'requires', [
        ('event.kind == "model_answered" => event.task != null and event.answer != null', lambda: ((not (event.kind == "model_answered")) or ((event.task is not None) and (event.answer is not None)))),
        ('event.kind == "sandbox_finished" => event.target != null and event.output != null', lambda: ((not (event.kind == "sandbox_finished")) or ((event.target is not None) and (event.output is not None)))),
    ])
    result = _flows.evaluate(state=state, event=event, cfg=cfg)
    _c.check('rptg.check:evaluate', 'ensures', [
        ('forall e in result: e.hard', lambda: all(e.hard for e in result)),
    ])
    return result


def answer(event: Event) -> Answer:
    """ответ модели после извлечения — тот же разбор, что у evaluate: вид, предмет, узел, значение карты или разложения, код функции; событие без ответа модели — вид none"""
    result = _flows.answer(event=event)
    _c.check('rptg.check:answer', 'ensures', [
        ('result.ok => result.error == null', lambda: ((not result.ok) or (result.error is None))),
        ('result.ok and result.kind == "function" => result.code != null', lambda: ((not (result.ok and (result.kind == "function"))) or (result.code is not None))),
    ])
    return result


def dead_ops(state: State) -> Strings:
    """операции, недостижимые от операций корня (I10), по порядку"""
    result = _flows.dead_ops(state=state)
    return result


def stale(state: State, changed: Strings) -> Strings:
    """что устаревает, когда изменились карточки узлов (LOGIC §7.7): вызывающие разложения, функции узла, сборки узла и предков"""
    result = _flows.stale(state=state, changed=changed)
    return result


def accepted(state: State, subject: Subject) -> Acceptance:
    """принят ли предмет: HARD pass от доверенной проверки на текущем хэше для каждого требуемого слоя. Хэш разложения — digest {design, card, uses — карточки узлов uses, types — типы владельцев-предков}"""
    result = _flows.accepted(state=state, subject=subject)
    _c.check('rptg.check:accepted', 'ensures', [
        ('result.accepted => len(result.missing) == 0', lambda: ((not result.accepted) or (len(result.missing) == 0))),
    ])
    return result


def report(evidence: Evidence, state: State) -> Report:
    """доказательство провала → самодостаточный отчёт для починки: место, нарушенный фрагмент, ожидание, контрпример"""
    _c.check('rptg.check:report', 'requires', [
        ('evidence.verdict == "fail"', lambda: (evidence.verdict == "fail")),
    ])
    result = _flows.report(evidence=evidence, state=state)
    _c.check('rptg.check:report', 'ensures', [
        ('result.subject == evidence.subject', lambda: (result.subject == evidence.subject)),
        ('result.layer == evidence.check', lambda: (result.layer == evidence.check)),
    ])
    return result


def run_case(case: ControlCase, cfg: Config) -> CaseResult:
    """прогнать один контрольный случай через свою проверку"""
    result = _flows.run_case(case=case, cfg=cfg)
    _c.check('rptg.check:run_case', 'ensures', [
        ('result.id == case.id', lambda: (result.id == case.id)),
        ('result.ok == (result.actual == result.expected)', lambda: (result.ok == (result.actual == result.expected))),
    ])
    return result


def summarize(results: CaseResults) -> SelftestReport:
    """итоги контрольных случаев → сводка по проверкам"""
    _c.check('rptg.check:summarize', 'requires', [
        ('len(results) >= 1', lambda: (len(results) >= 1)),
    ])
    result = _flows.summarize(results=results)
    _c.check('rptg.check:summarize', 'ensures', [
        ('forall r in result.checks: r.trusted == (r.failed == 0)', lambda: all((r.trusted == (r.failed == 0)) for r in result.checks)),
        ('forall r in result.checks: r.passed + r.failed >= 1', lambda: all(((r.passed + r.failed) >= 1) for r in result.checks)),
    ])
    return result
