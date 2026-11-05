"""Схемы потоков узла rptg.check.

Сгенерировано tools/codegen0.py по design/rptg.check.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg.check._types import Parts
from . import answer as c_answer
from ._leaves import cases as c_cases
from . import code as c_code
from . import contract as c_contract
from . import graph as c_graph
from rptg import lang as u_lang
from . import verdict as c_verdict



def evaluate(state, event, cfg):
    n1 = c_answer.extract(event=_v.dump(event))
    n2 = c_answer.form(state=_v.dump(state), answer=n1, cfg=cfg)
    n3 = c_graph.structure(state=_v.dump(state), answer=n1, form=n2, cfg=cfg)
    n4 = c_contract.data(state=_v.dump(state), answer=n1, form=n2, cfg=cfg, edges=_v.dump([]))
    n5 = c_contract.logic(state=_v.dump(state), answer=n1, form=n2, cfg=cfg)
    n6 = c_contract.examples(state=_v.dump(state), answer=n1, form=n2, cfg=cfg)
    n7 = c_code.static(state=_v.dump(state), answer=n1, cfg=cfg)
    n8 = c_code.runs(state=_v.dump(state), event=_v.dump(event), cfg=cfg)
    n9 = Parts(form=n2, structure=n3, data=n4, logic=n5, examples=n6, static=n7, runs=n8)
    n10 = c_verdict.subject(state=_v.dump(state), event=_v.dump(event), answer=n1)
    n11 = u_lang.digest(value=_v.dump(n10.content))
    n12 = c_verdict.assemble(parts=n9, subject=n10, digest=n11, cfg=cfg)
    return n12


def answer(event):
    n1 = c_answer.extract(event=_v.dump(event))
    return n1


def dead_ops(state):
    n1 = c_graph.dead_ops(state=_v.dump(state))
    return n1


def stale(state, changed):
    n1 = c_graph.stale(state=_v.dump(state), changed=changed)
    return n1


def accepted(state, subject):
    n1 = c_verdict.accepted(state=_v.dump(state), subject=subject)
    return n1


def report(evidence, state):
    n1 = c_verdict.report(evidence=evidence, state=_v.dump(state))
    return n1


def run_case(case, cfg):
    n0 = c_cases.unpack(case=case)
    n1 = c_answer.extract(event=_v.dump(n0.event))
    n2 = c_answer.form(state=_v.dump(n0.state), answer=n1, cfg=cfg)
    n3 = c_graph.structure(state=_v.dump(n0.state), answer=n1, form=n2, cfg=cfg)
    n4 = c_contract.data(state=_v.dump(n0.state), answer=n1, form=n2, cfg=cfg, edges=_v.dump(n0.edges))
    n5 = c_contract.logic(state=_v.dump(n0.state), answer=n1, form=n2, cfg=cfg)
    n6 = c_contract.examples(state=_v.dump(n0.state), answer=n1, form=n2, cfg=cfg)
    n7 = c_code.static(state=_v.dump(n0.state), answer=n1, cfg=cfg)
    n8 = c_code.runs(state=_v.dump(n0.state), event=_v.dump(n0.event), cfg=cfg)
    n9 = Parts(form=n2, structure=n3, data=n4, logic=n5, examples=n6, static=n7, runs=n8)
    n10 = c_verdict.subject(state=_v.dump(n0.state), event=_v.dump(n0.event), answer=n1)
    n11 = u_lang.digest(value=_v.dump(n10.content))
    n12 = c_verdict.assemble(parts=n9, subject=n10, digest=n11, cfg=cfg)
    n13 = c_cases.pick(case=case, evidences=n12)
    return n13


def summarize(results):
    n1 = c_cases.summarize(results=results)
    return n1
