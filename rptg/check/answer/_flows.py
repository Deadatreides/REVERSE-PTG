"""Схемы потоков узла rptg.check.answer.

Сгенерировано tools/codegen0.py по design/rptg.check.answer.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import conds as c_conds
from ._leaves import judge as c_judge
from rptg import lang as u_lang
from ._leaves import names as c_names
from ._leaves import raw as c_raw
from ._leaves import shape as c_shape



def extract(event):
    n1 = c_raw.extract(event=_v.dump(event))
    return n1


def form(state, answer, cfg):
    n1 = c_shape.jobs(state=_v.dump(state), answer=answer)
    n2 = [u_lang.type_validate(value=_v.dump(_x.value), type=_x.type, env=_x.env) for _x in n1]
    n3 = c_conds.jobs(state=_v.dump(state), answer=answer, checked=n2)
    n4 = c_names.problems(state=_v.dump(state), answer=answer, checked=n2)
    n5 = [u_lang.cl_info(text=_x.text, env=_x.env) for _x in n3]
    n6 = c_judge.form(answer=answer, shape=n1, checked=n2, problems=n4, conds=n3, infos=n5)
    return n6
