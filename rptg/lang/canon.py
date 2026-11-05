"""Лист rptg.lang.canon — каноническая запись JSON и хэш (то же правило, что canonical_json в arch2).

Функции приняты по карточке design/rptg.lang.yaml; обвязку пишет скрипт.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Json, Sha


def canonical(value: Json) -> str:
    """Ключи по порядку, без пробелов, UTF-8 без экранирования."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Json) -> Sha:
    """SHA-256 канонической записи, шестнадцатерично."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
