"""Схемы потоков узла rptg.check.verdict.

Сгенерировано tools/codegen0.py по design/rptg.check.verdict.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import accept as c_accept
from ._leaves import applied as c_applied
from ._leaves import content as c_content
from rptg import lang as u_lang
from ._leaves import order as c_order
from ._leaves import report as c_report



def subject(state, event, answer):
    n1 = c_applied.apply(state=_v.dump(state), event=_v.dump(event), answer=answer)
    n2 = c_content.of(state=_v.dump(n1.state), subject=n1.subject, raw=_v.dump(n1.raw))
    return n2.main


def assemble(parts, subject, digest, cfg):
    n1 = c_order.assemble(parts=parts, subject=subject, digest=digest, cfg=cfg)
    return n1


def accepted(state, subject):
    n1 = c_content.of(state=_v.dump(state), subject=subject, raw=_v.dump(None))
    n2 = u_lang.digest(value=_v.dump(n1.main.content))
    n3 = [u_lang.digest(value=_v.dump(_x.content)) for _x in n1.more]
    n4 = c_accept.judge(state=_v.dump(state), needed=n1, main=n2, more=n3)
    return n4


def report(evidence, state):
    n1 = c_report.report(evidence=evidence, state=_v.dump(state))
    return n1
