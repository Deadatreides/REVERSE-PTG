"""Лист rptg.check.answer.shape — задание проверить ответ по схеме метода (LOGIC §5 П1, шаг 2).

Функции приняты по карточке design/rptg.check.answer.yaml; обвязку пишет скрипт. Схемы метода —
сгенерированные данные типов корня: лист не читает файлов и не зовёт код проекта.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import SCHEMAS, TypeEnv
from rptg.check._types import ValidateJob

if TYPE_CHECKING:
    from rptg._types import Answer, Json
    from rptg.check._types import ValidateJobs


def jobs(state: Json, answer: Answer) -> ValidateJobs:
    """Ответ разложения — тип Design, карты — MapAnswer. Каждая запись схем закрыта
    (additionalProperties: false): лишний ключ иначе прошёл бы форму и уронил загрузку ответа в
    объекты уже в plan. Непрозрачный Json остаётся открытым. Ответ не извлечён или другого вида —
    заданий нет."""
    if not answer.ok or answer.kind not in ("map", "design"):
        return []

    def closed(s):
        if not isinstance(s, dict):
            return s
        out = dict(s)
        if isinstance(s.get("properties"), dict):
            out["properties"] = {k: closed(v) for k, v in s["properties"].items()}
            out.setdefault("additionalProperties", False)
        for key in ("items", "additionalProperties"):
            if isinstance(s.get(key), dict):
                out[key] = closed(s[key])
        for key in ("oneOf", "anyOf", "allOf"):
            if isinstance(s.get(key), list):
                out[key] = [closed(x) for x in s[key]]
        return out

    env = TypeEnv(types={name: closed(schema) for name, schema in SCHEMAS.items()}, vars={})
    return [ValidateJob(where="ответ", value=answer.value, type="Design" if answer.kind == "design" else "MapAnswer",
                        env=env)]
