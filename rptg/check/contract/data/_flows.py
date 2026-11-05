"""Схемы потоков узла rptg.check.contract.data.

Сгенерировано tools/codegen0.py по design/rptg.check.contract.data.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import edges as c_edges
from rptg import lang as u_lang
from ._leaves import outcome as c_outcome
from ._leaves import subs as c_subs



def check(state, answer, form, edges):
    n1 = c_edges.jobs(state=_v.dump(state), answer=answer, form=form, edges=_v.dump(edges))
    n2 = [u_lang.type_path(root=_x.root, path=_x.path, env=_x.env) for _x in n1.paths]
    n3 = [u_lang.type_validate(value=_v.dump(_x.value), type=_x.type, env=_x.env) for _x in n1.consts]
    n4 = c_subs.jobs(edges=n1, paths=n2)
    n5 = [u_lang.type_sub(a=_x.a, b=_x.b, env=_x.env) for _x in n4]
    n6 = c_outcome.verdict(edges=n1, paths=n2, consts=n3, subs=n4, results=n5)
    return n6
