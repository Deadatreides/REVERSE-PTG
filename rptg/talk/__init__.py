"""общение с моделями: подсказки по видам задач с устойчивым префиксом и версией, другая формулировка для повтора формы, отчёт в подсказке починки; запросы поставщикам по способу вывода; разбор ответов; цена

Сгенерировано tools/codegen0.py по design/rptg.talk.yaml — не править руками.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Config, Json, Operator, Prompt, ProviderRequest, RawAnswer, State, Task



def prompt(task: Task, state: State, cfg: Config) -> Prompt:
    """подсказка задачи: префикс роли и схема ответа — стабильны для кэша; тело — предмет, контекст, отчёт"""
    _c.check('rptg.talk:prompt', 'requires', [
        ('task.operator in cfg.operators', lambda: (task.operator in cfg.operators)),
    ])
    result = _flows.prompt(task=task, state=state, cfg=cfg)
    _c.check('rptg.talk:prompt', 'ensures', [
        ('len(result.prefix) >= 1', lambda: (len(result.prefix) >= 1)),
        ('len(result.body) >= 1', lambda: (len(result.body) >= 1)),
    ])
    return result


def request(prompt: Prompt, task: Task, cfg: Config) -> ProviderRequest:
    """подсказка → запрос поставщику по способу вывода оператора; ключи сюда не попадают"""
    _c.check('rptg.talk:request', 'requires', [
        ('task.operator in cfg.operators', lambda: (task.operator in cfg.operators)),
    ])
    result = _flows.request(prompt=prompt, task=task, cfg=cfg)
    _c.check('rptg.talk:request', 'ensures', [
        ('result.operator == task.operator', lambda: (result.operator == task.operator)),
    ])
    return result


def response(provider: str, raw: Json) -> RawAnswer:
    """разбор конверта ответа поставщика; отказ приводится к finish_reason refusal"""
    _c.check('rptg.talk:response', 'requires', [
        ('provider in {"anthropic", "openai", "google", "openrouter", "openai_compatible", "llamacpp"}', lambda: (provider in ("anthropic", "openai", "google", "openrouter", "openai_compatible", "llamacpp",))),
    ])
    result = _flows.response(provider=provider, raw=raw)
    _c.check('rptg.talk:response', 'ensures', [
        ('result.input_tokens >= 0 and result.output_tokens >= 0', lambda: ((result.input_tokens >= 0) and (result.output_tokens >= 0))),
        ('result.refusal => result.finish_reason == "refusal"', lambda: ((not result.refusal) or (result.finish_reason == "refusal"))),
    ])
    return result


def cost(answer: RawAnswer, operator: Operator) -> str:
    """цена ответа по ценам оператора за миллион токенов"""
    result = _flows.cost(answer=answer, operator=operator)
    _c.check('rptg.talk:cost', 'ensures', [
        ('result >= 0', lambda: (Decimal(result) >= 0)),
    ])
    return result
