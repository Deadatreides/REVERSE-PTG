"""Финальные дети узла rptg.talk в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.talk.yaml — не править руками.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import schema as _m_schema
from . import text as _m_text
from . import wire as _m_wire
from . import price as _m_price

if TYPE_CHECKING:
    from rptg._types import Config, Json, Operator, Prompt, ProviderRequest, RawAnswer, Task
    from rptg.talk._types import Facts, PromptText



class schema:
    """Лист rptg.talk.schema: операции в обёртках условий."""

    @staticmethod
    def answer(task: Task) -> Json:
        """карта — MapAnswer, разложение, ревизия и шаги split — Design, функция — null (ответ — блок python). Замыкание типов по ссылкам из схем корня; каждая запись с properties закрыта (additionalProperties: false) — как в П1; ссылка {$ref: Имя} → {$ref: #/$defs/Имя}; сам тип — вверху, остальные — в $defs"""
        result = _m_schema.answer(task=task)
        _c.check('rptg.talk.schema:answer', 'ensures', [
            ('task.kind == "function" => result == null', lambda: ((not (task.kind == "function")) or (result is None))),
            ('task.kind != "function" => result != null', lambda: ((not (task.kind != "function")) or (result is not None))),
        ])
        return result


class text:
    """Лист rptg.talk.text: операции в обёртках условий."""

    @staticmethod
    def render(task: Task, facts: Facts, schema: Json, mode: str, cfg: Config, texts: Json) -> PromptText:
        """тексты — texts[версия оператора]; префикс — общие строки, правила группы вида (ревизия и шаги split — группа разложения), строки языка условий, договор ответа: для функции — code, иначе договор способа, строка closed и схема JSON с ключами по порядку; тело — указание вида по формулировке (у другой формулировки — ещё строка формы), разделы фактов с заголовками (пустые значения пропускаются; строка — как есть, иначе JSON с отступом 1), после раздела отчёта — строки починки. Префикс не зависит ни от формулировки, ни от отчёта — кэш держится на повторах"""
        _c.check('rptg.talk.text:render', 'requires', [
            ('task.operator in cfg.operators', lambda: (task.operator in cfg.operators)),
        ])
        result = _m_text.render(task=task, facts=facts, schema=schema, mode=mode, cfg=cfg, texts=texts)
        _c.check('rptg.talk.text:render', 'ensures', [
            ('len(result.prefix) >= 1', lambda: (len(result.prefix) >= 1)),
            ('len(result.body) >= 1', lambda: (len(result.body) >= 1)),
        ])
        return result


class wire:
    """Лист rptg.talk.wire: операции в обёртках условий."""

    @staticmethod
    def mode(task: Task, cfg: Config) -> str:
        """способ вывода запроса. Функция — grammar, если его просит оператор и поставщик умеет (llamacpp), иначе prompt. Ответ JSON — первый доступный поставщику способ из предпочтений: json_schema → json_schema, tool, prompt; tool → tool, json_schema, prompt; grammar → grammar, json_schema, tool, prompt; prompt → prompt. Доступны: anthropic — tool, prompt (строгий json_schema не вмещает ответов rptg); openai, openrouter, openai_compatible — json_schema, tool, prompt; google — json_schema, prompt; llamacpp — grammar, json_schema, prompt"""
        _c.check('rptg.talk.wire:mode', 'requires', [
            ('task.operator in cfg.operators', lambda: (task.operator in cfg.operators)),
        ])
        result = _m_wire.mode(task=task, cfg=cfg)
        _c.check('rptg.talk.wire:mode', 'ensures', [
            ('result in {"json_schema", "tool", "grammar", "prompt"}', lambda: (result in ("json_schema", "tool", "grammar", "prompt",))),
            ('task.kind == "function" => result == "grammar" or result == "prompt"', lambda: ((not (task.kind == "function")) or ((result == "grammar") or (result == "prompt")))),
        ])
        return result

    @staticmethod
    def payload(prompt: Prompt, task: Task, mode: str, cfg: Config) -> ProviderRequest:
        """запрос по протоколу поставщика, ключей нет. Префикс — системная часть (у anthropic — блок с меткой кэша ephemeral), тело — сообщение пользователя. anthropic: tool — инструмент answer со схемой и tool_choice auto (принудительный выбор задают params: новые модели его не принимают). openai, openrouter, openai_compatible: json_schema — response_format со схемой без strict, tool — функция answer и выбор её; endpoint — у openrouter свой, у openai_compatible — base_url оператора. google: json_schema — response_mime_type application/json и response_json_schema в config. llamacpp: функция в grammar — GBNF одного блока python, JSON-ответ в grammar и json_schema — response_format со схемой. params оператора — поверх, как есть (у google — в config)"""
        _c.check('rptg.talk.wire:payload', 'requires', [
            ('task.operator in cfg.operators', lambda: (task.operator in cfg.operators)),
        ])
        result = _m_wire.payload(prompt=prompt, task=task, mode=mode, cfg=cfg)
        _c.check('rptg.talk.wire:payload', 'ensures', [
            ('result.operator == task.operator', lambda: (result.operator == task.operator)),
            ('result.mode == mode', lambda: (result.mode == mode)),
        ])
        return result

    @staticmethod
    def read(provider: str, raw: Json) -> RawAnswer:
        """конверт → текст, токены, причина, отказ; содержимое не разбирается. Текст: у anthropic — вход первого вызова инструмента в JSON, иначе блоки text подряд (блоки мышления пропускаются); у openai-подобных (openai, openrouter, openai_compatible, llamacpp) — аргументы первого вызова функции, иначе content; у google — аргументы вызова функции в JSON, иначе текстовые части без мыслей. Входные токены — по полной цене: у anthropic input_tokens и запись в кэш, у openai-подобных и google — вход минус прочитанное из кэша, не меньше нуля; прочитанное из кэша — отдельно; выход google — кандидаты и мысли. Отказ: stop_reason refusal (anthropic), поле refusal или content_filter (openai-подобные), причина блокировки подсказки или причина остановки SAFETY, RECITATION, BLOCKLIST, PROHIBITED_CONTENT, SPII, IMAGE_SAFETY (google) — тогда finish_reason refusal; иначе finish_reason поставщика как есть"""
        _c.check('rptg.talk.wire:read', 'requires', [
            ('provider in {"anthropic", "openai", "google", "openrouter", "openai_compatible", "llamacpp"}', lambda: (provider in ("anthropic", "openai", "google", "openrouter", "openai_compatible", "llamacpp",))),
        ])
        result = _m_wire.read(provider=provider, raw=raw)
        _c.check('rptg.talk.wire:read', 'ensures', [
            ('result.input_tokens >= 0 and result.output_tokens >= 0', lambda: ((result.input_tokens >= 0) and (result.output_tokens >= 0))),
            ('result.refusal => result.finish_reason == "refusal"', lambda: ((not result.refusal) or (result.finish_reason == "refusal"))),
        ])
        return result


class price:
    """Лист rptg.talk.price: операции в обёртках условий."""

    @staticmethod
    def cost(answer: RawAnswer, operator: Operator) -> str:
        """(вход × input + выход × output + прочитанное из кэша × cache) / 10⁶; нет цены кэша — чтение из кэша по цене входа. Счёт в целых с общим масштабом, запись — десятичная без хвостовых нулей, ноль — «0». Запись в кэш у Anthropic идёт по цене входа: надбавки в Price нет"""
        result = _m_price.cost(answer=answer, operator=operator)
        _c.check('rptg.talk.price:cost', 'ensures', [
            ('result >= 0', lambda: (Decimal(result) >= 0)),
        ])
        return result
