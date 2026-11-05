"""Лист rptg.check.answer.raw — извлечение ответа модели из сырого текста (LOGIC §5 П1, §8.3).

Функции приняты по карточке design/rptg.check.answer.yaml; обвязку пишет скрипт. Извлечение —
внутри проверки: в arch1 59,6 % первичных FAIL были ложными из-за извлечения вне неё.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from rptg._types import Answer

if TYPE_CHECKING:
    from rptg._types import Json


def extract(event: Json) -> Answer:
    """Карта и разложение — весь текст как JSON (json_schema, tool, grammar) или единственный блок
    json (prompt); функция — единственный блок python у любого поставщика. Мысли <think> снимаются
    до поиска блоков; метка блока — без учёта регистра, у python ещё py и python3; блок без метки
    — только когда помеченных нет. Несколько блоков — провал формы, а не выбор (arch1, этап 8).
    Узел и операция — из предмета задачи; у разложения узел дописывается в ответ. Обрыв по
    пределу длины — пометка truncated, не ошибка модели; отказ, неизвестный вид задачи и шаг
    split — не извлечено."""
    if event.get("kind") != "model_answered":
        return Answer(ok=False, kind="none", subject="", node="", truncated=False, error="событие без ответа модели")
    task, raw = event["task"], event["answer"]
    kind = {"map": "map", "design": "design", "revision": "design", "function": "function", "design_r1": "design_step",
            "design_r2": "design_step", "design_r3": "design_step"}.get(task["kind"], "none")
    node, _, op = task["subject"].partition(":")[2].partition(":")
    base = {"kind": kind, "subject": task["subject"], "node": node, "op": op or None,
            "truncated": raw["finish_reason"].lower() in ("length", "max_tokens", "max_output_tokens")}

    def visible(text):
        """Мысли модели снимаются до поиска блоков: в них бывают свои блоки кода. Незакрытый <think>
        у Qwen3 с /no_think стоит прямо перед ответом — тогда снимается один тег (мицелий:
        наивная вырезка до конца обнулила 29 ответов из 30)."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        head, mark, tail = text.partition("<think>")
        if mark and not ("```" in tail or tail.lstrip().startswith(("{", "["))):
            tail = ""
        return (head + tail).strip()

    text = visible(raw["text"])

    def fenced(tags, what):
        tagged = re.findall(r"```(?:" + tags + r")[ \t]*\n(.*?)```", text, re.S | re.I)
        blocks = tagged or re.findall(r"```[ \t]*\n(.*?)```", text, re.S)
        if len(blocks) == 1:
            return blocks[0], None
        return None, f"в ответе {'нет блока' if not blocks else 'несколько блоков'} {what}"

    def parsed():
        body, error = text, None
        if not body.startswith(("{", "[")):
            body, error = fenced("json", "JSON")
        try:
            value = None if error else json.loads(body)
        except ValueError as e:
            return None, f"JSON не разбирается: {e}"
        if error or not isinstance(value, dict):
            return None, error or "ответ — не объект JSON"
        if kind == "design" and value.get("node", node) != node:
            return None, f"узел в ответе — {value['node']}, а задача — {node}"
        return ({**value, "node": node} if kind == "design" else value), None

    reason = "модель отказалась отвечать" if raw["refusal"] else {
        "none": f"вид задачи {task['kind']} проверке неизвестен",
        "design_step": "пошаговое разложение проверкой ещё не поддержано"}.get(kind)
    if reason:
        return Answer(ok=False, error=reason, **base)
    if kind == "function":
        code, error = fenced("python3|python|py", "python")
        return Answer(ok=error is None, code=code, error=error, **base)
    value, error = parsed()
    return Answer(ok=error is None, value=value, error=error, **base)
