"""Лист rptg.talk.text — текст подсказки по текстам версии оператора (LOGIC §8.1–§8.4).

Функции приняты по карточке design/rptg.talk.yaml; обвязку пишет скрипт. Тексты — данные разложения
(texts_p1): они входят в его хэш, и правка текста снимает утверждение (MODEL_INTERFACE §2).
Префикс не зависит ни от формулировки, ни от отчёта: у повтора формы и у починки он тот же, и кэш
поставщика держится. Другая формулировка меняет только указание задачи — факты те же
(experiment13). Отчёт приходит разделом фактов (контекст починки), прежнего ответа нет (F1).
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rptg.talk._types import PromptText

if TYPE_CHECKING:
    from rptg._types import Config, Json, Task
    from rptg.talk._types import Facts


def render(task: Task, facts: Facts, schema: Json, mode: str, cfg: Config, texts: Json) -> PromptText:
    """Префикс — общие строки, правила группы вида, язык условий, договор ответа (функция — code,
    иначе договор способа, строка closed и схема JSON с ключами по порядку). Тело — указание вида по
    формулировке (у другой — ещё строка формы), непустые разделы фактов с заголовками (строка — как
    есть, иначе JSON с отступом 1), после раздела отчёта — строки починки."""
    version = cfg.operators[task.operator].prompt_version
    t = texts[version]
    key = {"design_r1": "design", "design_r2": "design", "design_r3": "design"}.get(task.kind, task.kind)
    group = {"revision": "design"}.get(key, key)
    node, _, op = task.subject.partition(":")[2].partition(":")
    marks = {"<role>": task.role, "<node>": node, "<op>": op, "<subject>": task.subject}

    def fill(line):
        for mark, value in marks.items():
            line = line.replace(mark, value)
        return line

    head = [fill(line) for line in t["common"]] + t["rules"][group] + t["cl"]
    if schema is None:
        head.append(t["contract"]["code"])
    else:
        head += [t["contract"][mode], t["contract"]["closed"], json.dumps(schema, ensure_ascii=False, sort_keys=True)]
    body = [fill(t["instruction"][task.wording][key])] + ([t["form"]] if task.wording == "alternative" else [])
    for fact in facts.sections:
        if fact.value in ("", [], {}):
            continue
        shown = fact.value if isinstance(fact.value, str) else json.dumps(fact.value, ensure_ascii=False, indent=1)
        body.append(f"## {t['titles'][fact.key]}\n{shown}")
        if fact.key == "report":
            body += t["repair"]
    return PromptText(prefix="\n".join(head), body="\n\n".join(body), version=version)
