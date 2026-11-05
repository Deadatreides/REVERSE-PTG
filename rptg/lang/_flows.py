"""Схемы потоков узла rptg.lang.

Сгенерировано tools/codegen0.py по design/rptg.lang.yaml — не править руками.
"""
from __future__ import annotations

from rptg import _values as _v
from ._leaves import canon as c_canon
from . import cl as c_cl
from ._leaves import types as c_types



def cl_info(text, env):
    n1 = c_cl.info(text=text, env=env)
    return n1


def cl_eval(text, env, values):
    n1 = c_cl.eval(text=text, env=env, values=_v.dump(values))
    return n1


def cl_python(text, env):
    n1 = c_cl.python(text=text, env=env)
    return n1


def cl_prove(facts, goal, env, limits):
    n1 = c_cl.prove(facts=facts, goal=goal, env=env, limits=limits)
    return n1


def cl_sat(conds, env, limits):
    n1 = c_cl.sat(conds=conds, env=env, limits=limits)
    return n1


def cl_strategy(requires, params, env):
    n1 = c_cl.strategy(requires=requires, params=params, env=env)
    return n1


def type_env(types, vars):
    n1 = c_types.env(types=types, vars=vars)
    return n1


def type_path(root, path, env):
    n1 = c_types.path(root=root, path=path, env=env)
    return n1


def type_sub(a, b, env):
    n1 = c_types.sub(a=a, b=b, env=env)
    return n1


def type_validate(value, type, env):
    n1 = c_types.validate(value=_v.dump(value), type=type, env=env)
    return n1


def type_size(type, env):
    n1 = c_types.size(type=type, env=env)
    return n1


def canonical(value):
    n1 = c_canon.canonical(value=_v.dump(value))
    return n1


def digest(value):
    n1 = c_canon.digest(value=_v.dump(value))
    return n1
