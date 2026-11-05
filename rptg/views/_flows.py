"""Схемы потоков узла rptg.views.

Сгенерировано tools/codegen0.py по design/rptg.views.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg import check as u_check
from ._leaves import graph as c_graph
from ._leaves import node as c_node
from ._leaves import outcomes as c_outcomes
from ._leaves import pick as c_pick
from ._leaves import status as c_status



def show(state, query, cfg):
    n1 = c_node.subjects(state=_v.dump(state), query=query)
    n2 = [u_check.accepted(state=state, subject=_x) for _x in n1]
    n3 = c_status.count(state=_v.dump(state))
    n4 = c_node.view(state=_v.dump(state), query=query, subjects=n1, acceptances=n2)
    n5 = c_graph.build(state=_v.dump(state))
    n8 = c_graph.paint(state=_v.dump(state), graph=_v.dump(n5))
    n6 = c_outcomes.rows(state=_v.dump(state))
    n7 = c_pick.view(query=query, status=_v.dump(n3), node=_v.dump(n4), graph=_v.dump(n8), competence=_v.dump(n6))
    return n7
