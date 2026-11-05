"""язык условий CL и язык типов: разбор, типизация, меры, вычисление, перевод в Python, доказательство через SMT-LIB и Z3, стратегии Hypothesis; окружение и пути типов, подтипы, проверка значений; каноническая запись и хэш

Сгенерировано tools/codegen0.py по design/rptg.lang.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Cl, ClInfo, Cls, EnvResult, EvalResult, Json, Limits, Params, PathType, Proof, Sat, Sha, StrMap, SubResult, TypeDefs, TypeEnv, Validation



def cl_info(text: Cl, env: TypeEnv) -> ClInfo:
    """разбор и типизация условия, его меры: узлы, кванторы, нелинейность, арифметика, строки, свободные имена"""
    result = _flows.cl_info(text=text, env=env)
    _c.check('rptg.lang:cl_info', 'ensures', [
        ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
        ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
    ])
    return result


def cl_eval(text: Cl, env: TypeEnv, values: Json) -> EvalResult:
    """значение условия на данных; деление на ноль даёт ложь"""
    result = _flows.cl_eval(text=text, env=env, values=values)
    _c.check('rptg.lang:cl_eval', 'ensures', [
        ('result.ok => result.error == null', lambda: ((not result.ok) or (result.error is None))),
    ])
    return result


def cl_python(text: Cl, env: TypeEnv) -> str:
    """условие → выражение Python для обёрток и тестов"""
    result = _flows.cl_python(text=text, env=env)
    _c.check('rptg.lang:cl_python', 'ensures', [
        ('len(result) >= 1', lambda: (len(result) >= 1)),
    ])
    return result


def cl_prove(facts: Cls, goal: Cl, env: TypeEnv, limits: Limits) -> Proof:
    """доказать: факты влекут цель, для списков длины до limits.k_lists; кодирование в SMT-LIB, решатель с детерминированным пределом ресурсов"""
    result = _flows.cl_prove(facts=facts, goal=goal, env=env, limits=limits)
    _c.check('rptg.lang:cl_prove', 'ensures', [
        ('result.verdict == "refuted" => result.counterexample != null', lambda: ((not (result.verdict == "refuted")) or (result.counterexample is not None))),
        ('result.bound == limits.k_lists', lambda: (result.bound == limits.k_lists)),
    ])
    return result


def cl_sat(conds: Cls, env: TypeEnv, limits: Limits) -> Sat:
    """выполним ли набор условий; если нет — номера строк противоречивого поднабора"""
    result = _flows.cl_sat(conds=conds, env=env, limits=limits)
    _c.check('rptg.lang:cl_sat', 'ensures', [
        ('result.verdict == "unsat" => len(result.core) >= 1', lambda: ((not (result.verdict == "unsat")) or (len(result.core) >= 1))),
        ('forall i in result.core: i >= 0 and i < len(conds)', lambda: all(((i >= 0) and (i < len(conds))) for i in result.core)),
    ])
    return result


def cl_strategy(requires: Cls, params: Params, env: TypeEnv) -> StrMap:
    """требования и параметры → стратегия Hypothesis на каждый параметр; простые сравнения с константами становятся границами"""
    result = _flows.cl_strategy(requires=requires, params=params, env=env)
    _c.check('rptg.lang:cl_strategy', 'ensures', [
        ('len(result) == len(params)', lambda: (len(result) == len(params))),
    ])
    return result


def type_env(types: TypeDefs, vars: Params) -> EnvResult:
    """окружение типов: схемы нужных типов с разрешёнными ссылками и типы переменных"""
    result = _flows.type_env(types=types, vars=vars)
    _c.check('rptg.lang:type_env', 'ensures', [
        ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
    ])
    return result


def type_path(root: str, path: str, env: TypeEnv) -> PathType:
    """тип значения по пути внутри типа"""
    result = _flows.type_path(root=root, path=path, env=env)
    _c.check('rptg.lang:type_path', 'ensures', [
        ('not result.ok => result.error != null', lambda: ((not (not result.ok)) or (result.error is not None))),
    ])
    return result


def type_sub(a: str, b: str, env: TypeEnv) -> SubResult:
    """тип a — подтип типа b; если нет — значение-свидетель"""
    result = _flows.type_sub(a=a, b=b, env=env)
    return result


def type_validate(value: Json, type: str, env: TypeEnv) -> Validation:
    """проверить значение по типу"""
    result = _flows.type_validate(value=value, type=type, env=env)
    _c.check('rptg.lang:type_validate', 'ensures', [
        ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
        ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
    ])
    return result


def type_size(type: str, env: TypeEnv) -> int:
    """число узлов схемы: каждый объект, список и скаляр — один узел, ссылки раскрываются"""
    result = _flows.type_size(type=type, env=env)
    _c.check('rptg.lang:type_size', 'ensures', [
        ('result >= 1', lambda: (result >= 1)),
    ])
    return result


def canonical(value: Json) -> str:
    """каноническая запись JSON: ключи по порядку, без пробелов, UTF-8"""
    result = _flows.canonical(value=value)
    _c.check('rptg.lang:canonical', 'ensures', [
        ('len(result) >= 1', lambda: (len(result) >= 1)),
    ])
    return result


def digest(value: Json) -> Sha:
    """SHA-256 канонической записи"""
    result = _flows.digest(value=value)
    _c.check('rptg.lang:digest', 'ensures', [
        ('len(result) == 64', lambda: (len(result) == 64)),
    ])
    return result
