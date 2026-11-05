"""Типы, которыми владеет узел rptg.talk.

Сгенерировано tools/codegen0.py по design/rptg.talk.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import Json, Strings



@dataclass(kw_only=True)
class Fact:
    """раздел фактов задачи: ключ из закрытого списка и значение; прежнего ответа модели среди ключей нет (F1)"""
    key: str
    value: Json


@dataclass(kw_only=True)
class Facts:
    """факты задачи по правилу контекста LOGIC §8.1 — разделы в порядке подсказки"""
    sections: list[Fact]


@dataclass(kw_only=True)
class PromptText:
    """текст подсказки: устойчивый префикс, тело задачи и версия текстов"""
    prefix: str
    body: str
    version: str


@dataclass(kw_only=True)
class KindTexts:
    """указания задачи по виду: карта, разложение, ревизия, функция"""
    map: str
    design: str
    revision: str
    function: str


@dataclass(kw_only=True)
class Texts:
    """тексты подсказок одной версии: общие строки, правила по группам видов, язык условий, договоры ответа по способу вывода, указания по формулировке, строка формы, строки починки, заголовки разделов"""
    common: Strings
    rules: TextsRules
    cl: Strings
    contract: TextsContract
    instruction: TextsInstruction
    form: str
    repair: Strings
    titles: TextsTitles


@dataclass(kw_only=True)
class TextsRules:
    map: Strings
    design: Strings
    function: Strings


@dataclass(kw_only=True)
class TextsContract:
    json_schema: str
    grammar: str
    tool: str
    prompt: str
    code: str
    closed: str


@dataclass(kw_only=True)
class TextsInstruction:
    primary: KindTexts
    alternative: KindTexts


@dataclass(kw_only=True)
class TextsTitles:
    idea: str
    examples: str
    card: str
    path: str
    map: str
    uses: str
    types: str
    limits: str
    op: str
    purpose: str
    imports: str
    design: str
    below: str
    report: str


PromptTexts = dict[str, Texts]
"""тексты подсказок по версиям; версия оператора выбирает свои"""


SCHEMAS: dict[str, Any] = {
    'Fact': {'type': 'object', 'required': ['key', 'value'], 'properties': {'key': {'type': 'string', 'enum': ['idea', 'examples', 'card', 'path', 'map', 'uses', 'types', 'limits', 'op', 'purpose', 'imports', 'design', 'below', 'report']}, 'value': {'$ref': 'Json'}}},
    'Facts': {'type': 'object', 'required': ['sections'], 'properties': {'sections': {'type': 'array', 'items': {'$ref': 'Fact'}}}},
    'PromptText': {'type': 'object', 'required': ['prefix', 'body', 'version'], 'properties': {'prefix': {'type': 'string'}, 'body': {'type': 'string'}, 'version': {'type': 'string'}}},
    'KindTexts': {'type': 'object', 'required': ['map', 'design', 'revision', 'function'], 'properties': {'map': {'type': 'string'}, 'design': {'type': 'string'}, 'revision': {'type': 'string'}, 'function': {'type': 'string'}}},
    'Texts': {'type': 'object', 'required': ['common', 'rules', 'cl', 'contract', 'instruction', 'form', 'repair', 'titles'], 'properties': {'common': {'$ref': 'Strings'}, 'rules': {'type': 'object', 'required': ['map', 'design', 'function'], 'properties': {'map': {'$ref': 'Strings'}, 'design': {'$ref': 'Strings'}, 'function': {'$ref': 'Strings'}}}, 'cl': {'$ref': 'Strings'}, 'contract': {'type': 'object', 'required': ['json_schema', 'grammar', 'tool', 'prompt', 'code', 'closed'], 'properties': {'json_schema': {'type': 'string'}, 'grammar': {'type': 'string'}, 'tool': {'type': 'string'}, 'prompt': {'type': 'string'}, 'code': {'type': 'string'}, 'closed': {'type': 'string'}}}, 'instruction': {'type': 'object', 'required': ['primary', 'alternative'], 'properties': {'primary': {'$ref': 'KindTexts'}, 'alternative': {'$ref': 'KindTexts'}}}, 'form': {'type': 'string'}, 'repair': {'$ref': 'Strings'}, 'titles': {'type': 'object', 'required': ['idea', 'examples', 'card', 'path', 'map', 'uses', 'types', 'limits', 'op', 'purpose', 'imports', 'design', 'below', 'report'], 'properties': {'idea': {'type': 'string'}, 'examples': {'type': 'string'}, 'card': {'type': 'string'}, 'path': {'type': 'string'}, 'map': {'type': 'string'}, 'uses': {'type': 'string'}, 'types': {'type': 'string'}, 'limits': {'type': 'string'}, 'op': {'type': 'string'}, 'purpose': {'type': 'string'}, 'imports': {'type': 'string'}, 'design': {'type': 'string'}, 'below': {'type': 'string'}, 'report': {'type': 'string'}}}}},
    'PromptTexts': {'type': 'object', 'additionalProperties': {'$ref': 'Texts'}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
