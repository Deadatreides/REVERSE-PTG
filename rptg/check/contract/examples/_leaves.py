"""Финальные дети узла rptg.check.contract.examples в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.examples.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import samples as _m_samples
from . import outcome as _m_outcome

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json
    from rptg.check._types import Validations
    from rptg.check.contract.examples._types import EvalResults, SampleJobs



class samples:
    """Лист rptg.check.contract.examples.samples: операции в обёртках условий."""

    @staticmethod
    def jobs(state: Json, answer: Answer, form: Evidences) -> SampleJobs:
        """для каждого примера: вход по типам параметров, выход точного примера по типу результата; requires на входе; ensures на входе и result = out, только у точного примера; нарушения без языка: примеров меньше I15 (у корня ≥ 2 и хотя бы один пользователя), вход не по параметрам, «*» в точном примере, пример пользователя потерян"""
        result = _m_samples.jobs(state=state, answer=answer, form=form)
        return result


class outcome:
    """Лист rptg.check.contract.examples.outcome: операции в обёртках условий."""

    @staticmethod
    def verdict(jobs: SampleJobs, validations: Validations, evals: EvalResults) -> Evidences:
        """неприменимо — пусто; значение не по типу, условие ложно или не вычисляется, нарушения без языка — fail, в details правило I16 или I15, место и все нарушения; иначе pass"""
        _c.check('rptg.check.contract.examples.outcome:verdict', 'requires', [
            ('len(validations) == len(jobs.validations)', lambda: (len(validations) == len(jobs.validations))),
            ('len(evals) == len(jobs.evals)', lambda: (len(evals) == len(jobs.evals))),
        ])
        result = _m_outcome.verdict(jobs=jobs, validations=validations, evals=evals)
        _c.check('rptg.check.contract.examples.outcome:verdict', 'ensures', [
            ('len(result) <= 1', lambda: (len(result) <= 1)),
            ('forall e in result: e.check == "P7"', lambda: all((e.check == "P7") for e in result)),
        ])
        return result
