"""Схемы потоков узла rptg.

Сгенерировано tools/codegen0.py по design/rptg.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from . import bench as c_bench
from . import build as c_build
from . import check as c_check
from . import plan as c_plan
from . import talk as c_talk
from . import views as c_views



def plan_next(state, cfg, table):
    n1 = c_plan.candidates(state=state, cfg=cfg)
    n2 = [c_plan.assign(candidate=_x, table=table, cfg=cfg) for _x in n1]
    n3 = c_plan.pick(state=state, candidates=n1, assignments=n2, cfg=cfg)
    return n3


def apply_event(state, event, cfg):
    n1 = c_check.evaluate(state=state, event=event, cfg=cfg)
    n2 = c_plan.transition(state=state, event=event, evidence=n1, cfg=cfg)
    return n2


def render_call(task, state, cfg):
    n1 = c_talk.prompt(task=task, state=state, cfg=cfg)
    n2 = c_talk.request(prompt=n1, task=task, cfg=cfg)
    return n2


def read_answer(provider, raw):
    n1 = c_talk.response(provider=provider, raw=_v.dump(raw))
    return n1


def build_files(state, target, cfg):
    n1 = c_build.files(state=state, target=target, cfg=cfg)
    return n1


def calibration_plan(reference, operators, cfg):
    n1 = c_bench.plan(reference=reference, operators=operators, cfg=cfg)
    return n1


def competence(results, plan, cfg):
    n1 = c_bench.table(results=results, plan=plan, cfg=cfg)
    return n1


def selftest(cases, cfg):
    n1 = [c_check.run_case(case=_x, cfg=cfg) for _x in cases]
    n2 = c_check.summarize(results=n1)
    return n2


def view(state, query, cfg):
    n1 = c_views.show(state=state, query=query, cfg=cfg)
    return n1
