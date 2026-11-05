"""Лист rptg.talk.wire — протоколы поставщиков (LOGIC §8.3, ARCHITECTURE §5).

Функции приняты по карточке design/rptg.talk.yaml; обвязку пишет скрипт. Тело запроса — именованные
аргументы вызова официального SDK поставщика, ключей в нём нет: их добавляет оболочка. Строгий
структурный вывод Anthropic ответов rptg не вмещает (только закрытые записи без словарей), поэтому
json_schema там недоступен, и способ, которым сделан запрос, пишется в сам запрос. Параметры
поставщика из профиля идут как есть (F3, F4): своих умолчаний лист не вводит.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rptg._types import ProviderRequest, RawAnswer

if TYPE_CHECKING:
    from rptg._types import Config, Json, Prompt, Task


def mode(task: Task, cfg: Config) -> str:
    """Функция — grammar, если оператор его просит и поставщик умеет, иначе prompt. Ответ JSON —
    первый доступный поставщику способ из предпочтений способа оператора."""
    op = cfg.operators[task.operator]
    chat = ("json_schema", "tool", "prompt")
    has = {"anthropic": ("tool", "prompt"), "openai": chat, "openrouter": chat, "openai_compatible": chat,
           "google": ("json_schema", "prompt"), "llamacpp": ("grammar", "json_schema", "prompt")}[op.provider]
    if task.kind == "function":
        return "grammar" if op.output_mode == "grammar" and "grammar" in has else "prompt"
    prefer = {"json_schema": chat, "tool": ("tool", "json_schema", "prompt"),
              "grammar": ("grammar", "json_schema", "tool", "prompt"), "prompt": ("prompt",)}[op.output_mode]
    return next(m for m in prefer if m in has)


def payload(prompt: Prompt, task: Task, mode: str, cfg: Config) -> ProviderRequest:
    """Префикс — системная часть (у anthropic — блок с меткой кэша), тело — сообщение пользователя;
    схема — по способу: инструмент answer, response_format, response_json_schema или грамматика.
    params оператора — поверх (у google — в config)."""
    op = cfg.operators[task.operator]
    schema, params, endpoint = prompt.answer_schema, op.params or {}, None
    about = "The answer of the task: one JSON object of the answer schema."
    if op.provider == "anthropic":
        body = {"model": op.model, "system": [{"type": "text", "text": prompt.prefix, "cache_control": {"type": "ephemeral"}}],
                "messages": [{"role": "user", "content": prompt.body}]}
        if mode == "tool":
            body |= {"tools": [{"name": "answer", "description": about, "input_schema": schema}], "tool_choice": {"type": "auto"}}
    elif op.provider == "google":
        config = {"system_instruction": prompt.prefix}
        if mode == "json_schema":
            config |= {"response_mime_type": "application/json", "response_json_schema": schema}
        body = {"model": op.model, "contents": [{"role": "user", "parts": [{"text": prompt.body}]}], "config": config | params}
        return ProviderRequest(provider=op.provider, operator=task.operator, mode=mode, payload=body)
    else:
        body = {"model": op.model, "messages": [{"role": "system", "content": prompt.prefix}, {"role": "user", "content": prompt.body}]}
        if op.provider == "llamacpp":
            if mode == "grammar" and schema is None:
                body["grammar"] = 'root ::= "```python\\n" [^`]* "```"'
            elif mode in ("grammar", "json_schema"):
                body["response_format"] = {"type": "json_object", "schema": schema}
        else:
            endpoint = {"openrouter": "https://openrouter.ai/api/v1", "openai_compatible": op.base_url}.get(op.provider)
            if mode == "json_schema":
                body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema, "strict": False}}
            elif mode == "tool":
                body |= {"tools": [{"type": "function", "function": {"name": "answer", "description": about, "parameters": schema}}],
                         "tool_choice": {"type": "function", "function": {"name": "answer"}}}
    return ProviderRequest(provider=op.provider, operator=task.operator, mode=mode, endpoint=endpoint, payload=body | params)


def read(provider: str, raw: Json) -> RawAnswer:
    """Текст — вход первого вызова инструмента или функции в JSON, иначе текст без мыслей; вход —
    по полной цене (у anthropic с записью в кэш, у остальных без прочитанного из кэша), не меньше
    нуля; отказ — finish_reason refusal, иначе причина поставщика как есть."""
    def count(part, *keys):
        return sum((part or {}).get(k) or 0 for k in keys)

    def anthropic():
        blocks, usage = raw.get("content") or [], raw.get("usage")
        calls = [b["input"] for b in blocks if b.get("type") == "tool_use"]
        text = json.dumps(calls[0], ensure_ascii=False) if calls else "".join(b["text"] for b in blocks if b.get("type") == "text")
        reason = raw.get("stop_reason") or ""
        return (text, count(usage, "input_tokens", "cache_creation_input_tokens"), count(usage, "output_tokens"),
                count(usage, "cache_read_input_tokens"), reason, reason == "refusal")

    def google():
        cands = raw.get("candidates", [])
        first = cands[0] if cands else {}
        parts, usage = first.get("content", {}).get("parts", []), raw.get("usageMetadata", {})
        calls = [p["functionCall"].get("args", {}) for p in parts if "functionCall" in p]
        text = json.dumps(calls[0], ensure_ascii=False) if calls else "".join(p.get("text", "") for p in parts if not p.get("thought"))
        reason, cached = first.get("finishReason", ""), usage.get("cachedContentTokenCount", 0)
        refused = "blockReason" in raw.get("promptFeedback", {}) or reason in (
            "SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY")
        return (text, usage.get("promptTokenCount", 0) - cached,
                usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0), cached, reason, refused)

    def chat():
        choice = (raw.get("choices") or [{}])[0]
        message, usage = choice.get("message") or {}, raw.get("usage")
        calls = [c["function"]["arguments"] for c in message.get("tool_calls") or []]
        reason, cached = choice.get("finish_reason") or "", count((usage or {}).get("prompt_tokens_details"), "cached_tokens")
        return (calls[0] if calls else message.get("content") or "", count(usage, "prompt_tokens") - cached,
                count(usage, "completion_tokens"), cached, reason, message.get("refusal") is not None or reason == "content_filter")

    text, spent, out, cached, reason, refused = {"anthropic": anthropic, "google": google}.get(provider, chat)()
    return RawAnswer(text=text, input_tokens=max(spent, 0), output_tokens=out, cache_read_tokens=cached,
                     finish_reason="refusal" if refused else reason, refusal=refused)
