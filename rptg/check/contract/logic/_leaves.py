"""Финальные дети узла rptg.check.contract.logic в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.logic.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import facts as _m_facts
from . import equal as _m_equal
from . import feasible as _m_feasible
from . import render as _m_render
from . import outcome as _m_outcome

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json
    from rptg.check.contract.logic._types import FactPlan, Obligations, Proofs, SatJobs, Sats



class facts:
    """Лист rptg.check.contract.logic.facts: операции в обёртках условий."""

    @staticmethod
    def plan(state: Json, answer: Answer, form: Evidences, cfg: Config) -> FactPlan:
        """для каждой операции S узла: факты — requires(S); узлы схемы по порядку: вызов — обязательство requires(C)[параметры ↦ источники] и факт ensures(C)[… , result ↦ выход]; отображение и свёртка — то же для i < k_lists под условием len(список) > i, накопитель — n__accI, выход свёртки — шаг eq с накопителем под условием len(список) == i; запись — шаг eq на каждое поле-путь, поле-литерал — факт; индекс [k] в источнике — обязательство len > k; цели П5 — ensures(S)[result ↦ источник результата]. Составной литерал — в unknown или partial. У карты схем нет — план пуст"""
        result = _m_facts.plan(state=state, answer=answer, form=form, cfg=cfg)
        _c.check('rptg.check.contract.logic.facts:plan', 'ensures', [
            ('result.applicable or len(result.ops) == 0', lambda: (result.applicable or (len(result.ops) == 0))),
        ])
        return result


class equal:
    """Лист rptg.check.contract.logic.equal: операции в обёртках условий."""

    @staticmethod
    def expand(plan: FactPlan, cfg: Config) -> FactPlan:
        """каждый шаг eq — факты left.p == right.p по скалярным путям схемы: у записи — обязательные поля (необязательные — в partial), вглубь по вложенным записям; у списка — длина и элементы до k_lists под условием len(right) > i; словарь и непрозрачный Json — в partial; условие шага сохраняется и сочетается с условиями элементов. Остальные шаги и поля плана не меняются"""
        result = _m_equal.expand(plan=plan, cfg=cfg)
        _c.check('rptg.check.contract.logic.equal:expand', 'ensures', [
            ('forall o in result.ops: forall s in o.steps: s.kind != "eq"', lambda: all(all((s.kind != "eq") for s in o.steps) for o in result.ops)),
            ('result.applicable == plan.applicable', lambda: (result.applicable == plan.applicable)),
        ])
        return result


class feasible:
    """Лист rptg.check.contract.logic.feasible: операции в обёртках условий."""

    @staticmethod
    def jobs(state: Json, answer: Answer, form: Evidences) -> SatJobs:
        """для каждой операции детей (у карты — корня): requires выполнимо; requires ∧ ensures выполнимо хотя бы при одном результате; окружение — Decimal, Json, типы строгих предков и новые типы ответа, параметры, для второго — ещё result; неприменимо (не карта и не разложение или П1 не прошла) — пусто"""
        result = _m_feasible.jobs(state=state, answer=answer, form=form)
        return result


class render:
    """Лист rptg.check.contract.logic.render: операции в обёртках условий."""

    @staticmethod
    def obligations(plan: FactPlan) -> Obligations:
        """в тексте шага имя параметра, стоящее не после точки и не в строке, заменяется своим выражением; переменная квантора получает имя q__v; шаг с условием — «(guard) => (текст)». Обязательство и цель П5 получают факты всех шагов-фактов выше себя в своей операции; в details обязательства — obligation, его текст без условия шага"""
        _c.check('rptg.check.contract.logic.render:obligations', 'requires', [
            ('forall o in plan.ops: forall s in o.steps: s.kind != "eq"', lambda: all(all((s.kind != "eq") for s in o.steps) for o in plan.ops)),
        ])
        result = _m_render.obligations(plan=plan)
        _c.check('rptg.check.contract.logic.render:obligations', 'ensures', [
            ('result.applicable == plan.applicable', lambda: (result.applicable == plan.applicable)),
        ])
        return result


class outcome:
    """Лист rptg.check.contract.logic.outcome: операции в обёртках условий."""

    @staticmethod
    def verdict(obligations: Obligations, proofs: Proofs, empties: SatJobs, sats: Sats, refines: Proofs) -> Evidences:
        """неприменимо — пусто; П4: невыполнимые условия — fail с противоречивым набором (I14), он называется первым: при противоречии обязательства ниже бессмысленны; иначе опровергнутое обязательство — fail с его details и контрпримером по путям параметров операции (unknown, если контрпример задевает путь с неполными фактами — он может быть ложным); unknown решателя или плана — unknown, иначе pass; П5 — так же по целям, если p5"""
        _c.check('rptg.check.contract.logic.outcome:verdict', 'requires', [
            ('len(proofs) == len(obligations.proofs)', lambda: (len(proofs) == len(obligations.proofs))),
            ('len(sats) == len(empties)', lambda: (len(sats) == len(empties))),
            ('len(refines) == len(obligations.refines)', lambda: (len(refines) == len(obligations.refines))),
        ])
        result = _m_outcome.verdict(obligations=obligations, proofs=proofs, empties=empties, sats=sats, refines=refines)
        _c.check('rptg.check.contract.logic.outcome:verdict', 'ensures', [
            ('len(result) <= 2', lambda: (len(result) <= 2)),
            ('forall e in result: e.check == "P4" or e.check == "P5"', lambda: all(((e.check == "P4") or (e.check == "P5")) for e in result)),
        ])
        return result
