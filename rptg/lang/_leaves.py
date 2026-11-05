"""Финальные дети узла rptg.lang в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.lang.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import types as _m_types
from . import canon as _m_canon

if TYPE_CHECKING:
    from rptg._types import EnvResult, Json, Params, PathType, Sha, SubResult, TypeDefs, TypeEnv, Validation



class types:
    """Лист rptg.lang.types: операции в обёртках условий."""

    @staticmethod
    def env(types: TypeDefs, vars: Params) -> EnvResult:
        """окружение: схемы нужных типов с разрешёнными ссылками и типы переменных"""
        result = _m_types.env(types=types, vars=vars)
        _c.check('rptg.lang.types:env', 'ensures', [
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
        ])
        return result

    @staticmethod
    def path(root: str, path: str, env: TypeEnv) -> PathType:
        """тип значения по пути внутри типа"""
        result = _m_types.path(root=root, path=path, env=env)
        _c.check('rptg.lang.types:path', 'ensures', [
            ('not result.ok => result.error != null', lambda: ((not (not result.ok)) or (result.error is not None))),
        ])
        return result

    @staticmethod
    def sub(a: str, b: str, env: TypeEnv) -> SubResult:
        """тип a — подтип типа b; если нет — свидетель"""
        result = _m_types.sub(a=a, b=b, env=env)
        return result

    @staticmethod
    def validate(value: Json, type: str, env: TypeEnv) -> Validation:
        """проверить значение по типу"""
        result = _m_types.validate(value=value, type=type, env=env)
        _c.check('rptg.lang.types:validate', 'ensures', [
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
            ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
        ])
        return result

    @staticmethod
    def size(type: str, env: TypeEnv) -> int:
        """число узлов схемы, ссылки раскрываются"""
        result = _m_types.size(type=type, env=env)
        _c.check('rptg.lang.types:size', 'ensures', [
            ('result >= 1', lambda: (result >= 1)),
        ])
        return result


class canon:
    """Лист rptg.lang.canon: операции в обёртках условий."""

    @staticmethod
    def canonical(value: Json) -> str:
        """ключи по порядку, без пробелов, UTF-8"""
        result = _m_canon.canonical(value=value)
        _c.check('rptg.lang.canon:canonical', 'ensures', [
            ('len(result) >= 1', lambda: (len(result) >= 1)),
        ])
        return result

    @staticmethod
    def digest(value: Json) -> Sha:
        """SHA-256 канонической записи"""
        result = _m_canon.digest(value=value)
        _c.check('rptg.lang.canon:digest', 'ensures', [
            ('len(result) == 64', lambda: (len(result) == 64)),
        ])
        return result
