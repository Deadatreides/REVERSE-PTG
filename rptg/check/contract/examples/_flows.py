"""Схемы потоков узла rptg.check.contract.examples.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.examples.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg import lang as u_lang
from ._leaves import outcome as c_outcome
from ._leaves import samples as c_samples



def check(state, answer, form):
    n1 = c_samples.jobs(state=_v.dump(state), answer=answer, form=form)
    n2 = [u_lang.type_validate(value=_v.dump(_x.value), type=_x.type, env=_x.env) for _x in n1.validations]
    n3 = [u_lang.cl_eval(text=_x.text, env=_x.env, values=_v.dump(_x.values)) for _x in n1.evals]
    n4 = c_outcome.verdict(jobs=n1, validations=n2, evals=n3)
    return n4
