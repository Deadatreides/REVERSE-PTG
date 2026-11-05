"""Типы, которыми владеет узел rptg.plan.

Сгенерировано tools/codegen0.py по design/rptg.plan.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rptg._types import ElementKind, Evidences, JournalEntry, Json, NodeId, Operator, PolicyNode, RawAnswer, Role, Sha, Strings, Subject, ViolationSubtype, WorkClass



@dataclass(kw_only=True)
class ReadyItem:
    """готовый к работе элемент в порядке очереди: предмет, вид элемента, роль, уровень узла, узел; op — операция функции"""
    subject: Subject
    kind: ElementKind
    role: Role
    level: int
    node: NodeId
    op: str | None = None


@dataclass(kw_only=True)
class KindDecision:
    """вид ребёнка по правилам LOGIC §6.2: rule — номер сработавшего правила или promotion (повышение, §7.4)"""
    node: NodeId
    kind: str
    rule: str


@dataclass(kw_only=True)
class Policies:
    """деревья политики по ролям (генотипы arch2, LOGIC §7.3) и дерево лишнего круга extra (после «оставить карточку» на исчерпанной лестнице); problems — нарушения валидатора, по роли"""
    architect: PolicyNode
    designer: PolicyNode
    implementer: PolicyNode
    extra: PolicyNode
    problems: Strings


@dataclass(kw_only=True)
class PolicyStep:
    """шаг политики элемента: wait — call (ждёт вызова модели), check (ждёт прогона), stop (конец с причиной stop), none (событие не двигает политику); path — новая позиция; у вызова — оператор, ступень, формулировка и нужен ли отчёт"""
    wait: str
    path: str
    stop: str
    operator: str
    rung: int
    wording: str
    report: bool


@dataclass(kw_only=True)
class Obs:
    """наблюдаемые элемента после события (LOGIC §7.3) и признаки для шага: complete — все требуемые проверки на текущем хэше есть или есть провал; unknown — ERROR или недоверенный pass без провала; repeat — ответ совпал по хэшу с прежним"""
    subtype: ViolationSubtype
    same: str
    attempts: int
    work: WorkClass
    tokens: int
    complete: bool
    accepted: bool
    unknown: bool
    repeat: bool


@dataclass(kw_only=True)
class EventFacts:
    """что принесло событие: вид события, предмет, узел и его уровень, роль, номер попытки задачи, элемент до события, провалы и unknown, текст и конверт ответа, профиль оператора для цены, ответ пользователя, разложение узла после события (чистый ответ разложения — он, иначе текущее); ready — элемент ответа без назначения, чтобы восстановить назначение без таблицы"""
    event: str
    subject: Subject
    node: str
    level: int
    role: str
    attempt: int
    element: Json
    failures: Evidences
    unknown: Evidences
    text: str
    raw: RawAnswer
    operator: Operator
    reply: Json
    design: Json
    ready: Ready


@dataclass(kw_only=True)
class Absorbed:
    """событие впитано: состояние с доказательствами, ответом и элементом после шага; route — узел, чьих детей надо разложить по видам (иначе пусто); design_hash — дайджест текущего разложения узла; notes — записи журнала"""
    state: Json
    facts: EventFacts
    obs: Obs
    step: PolicyStep
    route: str
    design_hash: Sha
    notes: list[JournalEntry]


@dataclass(kw_only=True)
class Settled:
    """следствия события: состояние, узлы с изменившимися карточками (для устаревания, LOGIC §7.7), записи журнала"""
    state: Json
    changed: Strings
    notes: list[JournalEntry]


Ready = list[ReadyItem]
"""готовые элементы в порядке очереди (LOGIC §7.1)"""

KindDecisions = list[KindDecision]
"""виды детей разложения по порядку детей"""


SCHEMAS: dict[str, Any] = {
    'ReadyItem': {'type': 'object', 'required': ['subject', 'kind', 'role', 'level', 'node'], 'properties': {'subject': {'$ref': 'Subject'}, 'kind': {'$ref': 'ElementKind'}, 'role': {'$ref': 'Role'}, 'level': {'type': 'integer', 'minimum': 1}, 'node': {'$ref': 'NodeId'}, 'op': {'type': 'string'}}},
    'Ready': {'type': 'array', 'items': {'$ref': 'ReadyItem'}},
    'KindDecision': {'type': 'object', 'required': ['node', 'kind', 'rule'], 'properties': {'node': {'$ref': 'NodeId'}, 'kind': {'type': 'string', 'enum': ['final', 'composite']}, 'rule': {'type': 'string'}}},
    'KindDecisions': {'type': 'array', 'items': {'$ref': 'KindDecision'}},
    'Policies': {'type': 'object', 'required': ['architect', 'designer', 'implementer', 'extra', 'problems'], 'properties': {'architect': {'$ref': 'PolicyNode'}, 'designer': {'$ref': 'PolicyNode'}, 'implementer': {'$ref': 'PolicyNode'}, 'extra': {'$ref': 'PolicyNode'}, 'problems': {'$ref': 'Strings'}}},
    'PolicyStep': {'type': 'object', 'required': ['wait', 'path', 'stop', 'operator', 'rung', 'wording', 'report'], 'properties': {'wait': {'type': 'string', 'enum': ['call', 'check', 'stop', 'none']}, 'path': {'type': 'string'}, 'stop': {'type': 'string'}, 'operator': {'type': 'string'}, 'rung': {'type': 'integer', 'minimum': 0}, 'wording': {'type': 'string', 'enum': ['primary', 'alternative']}, 'report': {'type': 'boolean'}}},
    'Obs': {'type': 'object', 'required': ['subtype', 'same', 'attempts', 'work', 'tokens', 'complete', 'accepted', 'unknown', 'repeat'], 'properties': {'subtype': {'$ref': 'ViolationSubtype'}, 'same': {'type': 'string', 'enum': ['SAME', 'DIFFERENT', 'NA']}, 'attempts': {'type': 'integer', 'minimum': 0}, 'work': {'$ref': 'WorkClass'}, 'tokens': {'type': 'integer', 'minimum': 0}, 'complete': {'type': 'boolean'}, 'accepted': {'type': 'boolean'}, 'unknown': {'type': 'boolean'}, 'repeat': {'type': 'boolean'}}},
    'EventFacts': {'type': 'object', 'required': ['event', 'subject', 'node', 'level', 'role', 'attempt', 'element', 'failures', 'unknown', 'text', 'raw', 'operator', 'reply', 'design', 'ready'], 'properties': {'event': {'type': 'string'}, 'subject': {'$ref': 'Subject'}, 'node': {'type': 'string'}, 'level': {'type': 'integer', 'minimum': 0}, 'role': {'type': 'string'}, 'attempt': {'type': 'integer', 'minimum': 0}, 'element': {'$ref': 'Json'}, 'failures': {'$ref': 'Evidences'}, 'unknown': {'$ref': 'Evidences'}, 'text': {'type': 'string'}, 'raw': {'$ref': 'RawAnswer'}, 'operator': {'$ref': 'Operator'}, 'reply': {'$ref': 'Json'}, 'design': {'$ref': 'Json'}, 'ready': {'$ref': 'Ready'}}},
    'Absorbed': {'type': 'object', 'required': ['state', 'facts', 'obs', 'step', 'route', 'design_hash', 'notes'], 'properties': {'state': {'$ref': 'Json'}, 'facts': {'$ref': 'EventFacts'}, 'obs': {'$ref': 'Obs'}, 'step': {'$ref': 'PolicyStep'}, 'route': {'type': 'string'}, 'design_hash': {'$ref': 'Sha'}, 'notes': {'type': 'array', 'items': {'$ref': 'JournalEntry'}}}},
    'Settled': {'type': 'object', 'required': ['state', 'changed', 'notes'], 'properties': {'state': {'$ref': 'Json'}, 'changed': {'$ref': 'Strings'}, 'notes': {'type': 'array', 'items': {'$ref': 'JournalEntry'}}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
