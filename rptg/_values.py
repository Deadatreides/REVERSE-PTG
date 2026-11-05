"""Значения на границе ядра: JSON ↔ dataclasses сгенерированных типов (LOGIC §5, Э6).

Ядро работает с объектами dataclasses, а карточки, примеры, журнал и хэши — с JSON. Перевод идёт
по аннотациям полей. Поле, чьё имя — слово Python (in, class), в объекте называется с
подчёркиванием, а в JSON — как в схеме (metadata["json"]). Необязательное поле без значения — None
в объекте и нет ключа в JSON. Непрозрачное значение (Json, Any) переходит как есть.
"""
import dataclasses
import types
import typing
from typing import Any

_HINTS: dict = {}


class BadValue(ValueError):
    """Значение JSON не подходит типу: путь внутри значения и причина."""


def hints(cls):
    if cls not in _HINTS:
        _HINTS[cls] = typing.get_type_hints(cls)
    return _HINTS[cls]


def load(tp, value, where="·"):
    """JSON → значение типа tp (класс dataclass, list[…], dict[str, …], X | None, простой тип, Any)."""
    if tp is Any:
        return value
    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        return load(next(a for a in args if a is not type(None)), value, where)
    if origin is list:
        if not isinstance(value, list):
            raise BadValue(f"{where}: ожидался список, стоит {value!r}")
        return [load(args[0], x, f"{where}[{i}]") for i, x in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise BadValue(f"{where}: ожидался словарь, стоит {value!r}")
        return {k: load(args[1], v, f"{where}.{k}") for k, v in value.items()}
    if dataclasses.is_dataclass(tp):
        return _load_record(tp, value, where)
    ok = isinstance(value, tp) and not (tp is int and isinstance(value, bool))
    if tp is float:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not ok:
        raise BadValue(f"{where}: ожидалось {tp.__name__}, стоит {value!r}")
    return value


def _load_record(cls, value, where):
    if not isinstance(value, dict):
        raise BadValue(f"{where}: ожидалась запись {cls.__name__}, стоит {value!r}")
    fields = {f.metadata.get("json", f.name): f for f in dataclasses.fields(cls)}
    extra = sorted(set(value) - set(fields))
    if extra:
        raise BadValue(f"{where}: у {cls.__name__} нет полей {', '.join(extra)}")
    kwargs = {}
    for key, f in fields.items():
        if key in value:
            kwargs[f.name] = load(hints(cls)[f.name], value[key], f"{where}.{key}")
        elif f.default is dataclasses.MISSING:
            raise BadValue(f"{where}: у {cls.__name__} нет обязательного поля {key}")
    return cls(**kwargs)


def dump(value):
    """Значение ядра → JSON: необязательные поля без значения не пишутся."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out = {}
        for f in dataclasses.fields(value):
            v = getattr(value, f.name)
            if v is None and f.default is None:
                continue
            out[f.metadata.get("json", f.name)] = dump(v)
        return out
    if isinstance(value, list):
        return [dump(x) for x in value]
    if isinstance(value, dict):
        return {k: dump(v) for k, v in value.items()}
    return value
