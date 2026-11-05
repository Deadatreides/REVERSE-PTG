"""Схемы потоков узла rptg.plan.machine.

Сгенерировано tools/codegen0.py по design/rptg.plan.machine.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from rptg._types import Evidence, State, Transition
from rptg import check as u_check
from ._leaves import close as c_close
from ._leaves import element as c_element
from ._leaves import intake as c_intake
from rptg import lang as u_lang
from ._leaves import policy as c_policy
from ._leaves import refresh as c_refresh
from rptg.plan import route as u_route
from ._leaves import settle as c_settle
from rptg import talk as u_talk



def absorb(state, event, evidence, answer, cfg):
    n1 = c_intake.facts(state=_v.dump(state), event=event, evidence=evidence, answer=answer, cfg=cfg)
    n2 = [u_check.report(evidence=_x, state=state) for _x in n1.failures]
    n3 = u_lang.digest(value=_v.dump(n1.text))
    n4 = u_talk.cost(answer=n1.raw, operator=n1.operator)
    n5 = u_route.score(state=_v.dump(state), ready=n1.ready, cfg=cfg)
    n6 = [u_route.fallback(candidate=_x, cfg=cfg) for _x in n5]
    n7 = c_intake.store(state=_v.dump(state), facts=n1, answer=answer, evidence=_v.dump(evidence), hash=n3, cost=n4, assignments=n6, cfg=cfg)
    n8 = u_check.accepted(state=_v.load(State, n7), subject=n1.subject)
    n9 = u_route.override(subject=n1.subject, cfg=cfg)
    n10 = c_policy.build(cfg=cfg)
    n11 = c_policy.check(policies=n10, cfg=cfg)
    n12 = c_intake.observe(state=_v.dump(n7), facts=n1, reports=n2, acceptance=n8, hash=n3)
    n13 = c_intake.idle(state=_v.dump(state), subject=n1.subject, assignments=n6)
    n14 = c_policy.step(policies=n11, state=_v.dump(n7), subject=n1.subject, obs=n12, idle=n13, manual=n9, event=n1.event, assignments=n6, cfg=cfg)
    n15 = u_lang.digest(value=_v.dump(n1.design))
    n16 = c_element.update(state=_v.dump(n7), facts=n1, obs=n12, step=n14, reports=_v.dump(n2), manual=n9, design_hash=n15)
    n17 = c_element.reply(absorbed=n16, cfg=cfg)
    n18 = c_element.decide(absorbed=n17, cfg=cfg)
    return n18


def settle(before, absorbed, kinds, cfg):
    n1 = c_settle.children(absorbed=absorbed, kinds=kinds, cfg=cfg)
    n4 = c_settle.revision(before=_v.dump(before), settled=n1, absorbed=absorbed)
    n2 = c_settle.suspect(settled=n4, absorbed=absorbed, cfg=cfg)
    n3 = c_settle.blame(settled=n2, absorbed=absorbed, cfg=cfg)
    return n3


def recheck(settled, cfg):
    n1 = u_check.dead_ops(state=_v.load(State, settled.state))
    n2 = c_refresh.remove(settled=settled, dead=n1, cfg=cfg)
    n12 = c_refresh.types(before=_v.dump(settled.state), settled=n2)
    n13 = c_refresh.restart(settled=n12)
    n3 = u_check.stale(state=_v.load(State, n13.state), changed=n13.changed)
    n4 = c_refresh.targets(settled=n13, stale=n3)
    n5 = [u_lang.canonical(value=_v.dump(_x)) for _x in n4.values]
    n6 = c_refresh.jobs(targets=n4, texts=n5, cfg=cfg)
    n7 = [u_check.evaluate(state=_v.load(State, n6.state), event=_x, cfg=cfg) for _x in n6.events]
    n8 = c_refresh.store(jobs=n6, results=_v.dump(n7))
    n9 = [u_check.accepted(state=_v.load(State, n8.state), subject=_x) for _x in n8.subjects]
    n10 = [u_check.report(evidence=_v.load(Evidence, _x), state=_v.load(State, n8.state)) for _x in n8.failures]
    n11 = c_refresh.apply(settled=n13, stored=n8, acceptances=n9, reports=_v.dump(n10), cfg=cfg)
    return n11


def close(before, absorbed, settled, evidence, cfg):
    n1 = c_close.phase(before=_v.dump(before), absorbed=absorbed, settled=settled, cfg=cfg)
    n2 = c_close.journal(before=_v.dump(before), after=_v.dump(n1), absorbed=absorbed, settled=settled, evidence=_v.dump(evidence))
    return _v.load(Transition, n2)


def policies(cfg):
    n1 = c_policy.build(cfg=cfg)
    n2 = c_policy.check(policies=n1, cfg=cfg)
    return n2


def dispatch(state, subject, assignments, cfg):
    n1 = u_route.override(subject=subject, cfg=cfg)
    n2 = c_policy.build(cfg=cfg)
    n3 = c_policy.check(policies=n2, cfg=cfg)
    n4 = c_intake.idle(state=_v.dump(state), subject=subject, assignments=assignments)
    n5 = c_policy.step(policies=n3, state=_v.dump(state), subject=subject, obs=n4, idle=n4, manual=n1, event='dispatch', assignments=assignments, cfg=cfg)
    return n5
