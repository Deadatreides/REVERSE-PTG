"""Схемы потоков узла rptg.plan.route.

Сгенерировано tools/codegen0.py по design/rptg.plan.route.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import decide as c_decide
from ._leaves import kind as c_kind
from rptg import lang as u_lang
from ._leaves import masks as c_masks
from ._leaves import measure as c_measure
from ._leaves import prior as c_prior



def score(state, ready, cfg):
    n1 = c_measure.envs(state=_v.dump(state), ready=ready)
    n2 = [u_lang.type_env(types=_x.types, vars=_x.vars) for _x in n1]
    n3 = c_measure.bind(state=_v.dump(state), ready=ready, envs=n2)
    n4 = [u_lang.cl_info(text=_x.text, env=_x.env) for _x in n3.conds]
    n5 = [u_lang.type_size(type=_x.type, env=_x.env) for _x in n3.sizes]
    n6 = [c_masks.resolve(subject=_x.node, cfg=cfg) for _x in ready]
    n8 = c_prior.classes(state=_v.dump(state), ready=ready, infos=n4)
    n7 = c_prior.candidates(state=_v.dump(state), ready=ready, infos=n4, sizes=n5, manual=n6, classes=n8, cfg=cfg)
    return n7


def assign(candidate, table, cfg):
    n1 = c_masks.resolve(subject=candidate.subject, cfg=cfg)
    n2 = c_decide.table(candidate=candidate, manual=n1, table=table, cfg=cfg)
    n3 = c_decide.assign(candidate=candidate, manual=n1, choice=n2, cfg=cfg)
    return n3


def fallback(candidate, cfg):
    n1 = c_masks.resolve(subject=candidate.subject, cfg=cfg)
    n2 = c_decide.assign(candidate=candidate, manual=n1, choice='', cfg=cfg)
    return n2


def kinds(state, node, cfg):
    n1 = c_kind.children(state=_v.dump(state), node=node)
    n2 = [c_masks.resolve(subject=_x, cfg=cfg) for _x in n1]
    n3 = c_kind.decide(state=_v.dump(state), children=n1, manual=n2, cfg=cfg)
    return n3


def override(subject, cfg):
    n1 = c_masks.resolve(subject=subject, cfg=cfg)
    return n1
