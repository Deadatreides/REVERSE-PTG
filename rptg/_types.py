"""Типы, которыми владеет узел rptg.

Сгенерировано tools/codegen0.py по design/types.yaml — не править руками.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any



@dataclass(kw_only=True)
class Example:
    """пример операции; match subset сравнивает только указанные поля, строка "*" — любое значение"""
    in_: Json = field(metadata={"json": 'in'})
    out: Json
    source: str
    match: str | None = None


@dataclass(kw_only=True)
class Param:
    """параметр операции"""
    name: str
    type: str


@dataclass(kw_only=True)
class Op:
    """операция узла"""
    name: str
    doc: str
    params: Params
    result: str
    requires: list[Cl]
    ensures: list[Cl]
    effects: list[Effect]
    examples: list[Example]


@dataclass(kw_only=True)
class Override:
    """ручное назначение на узел или маску (LOGIC §6.6)"""
    kind: str | None = None
    designer: str | None = None
    implementer: str | None = None
    start_rung: int | None = None
    max_rung: int | None = None
    approve: bool | None = None
    steps: str | None = None
    est_lines: int | None = None
    max_lines: int | None = None
    max_complexity: int | None = None


@dataclass(kw_only=True)
class NodeCard:
    """карточка узла — пишет тот, кто раскладывал родителя"""
    id: NodeId
    parent: NodeId | None = None
    owner: NodeId
    purpose: str
    uses: list[NodeId]
    effects: list[Effect]
    allowed_imports: list[str]
    est_lines: int
    ops: list[Op]


@dataclass(kw_only=True)
class TypeDef:
    """именованный тип"""
    name: str
    owner: NodeId
    doc: str | None = None
    schema: Json


@dataclass(kw_only=True)
class FlowNode:
    """узел схемы потока — ровно одно из call, map, fold, record"""
    id: str
    call: str | None = None
    map: str | None = None
    fold: str | None = None
    record: str | None = None
    over: Source | None = None
    init: Source | None = None
    acc: str | None = None
    item: str | None = None
    args: dict[str, Source] | None = None
    fields: dict[str, Source] | None = None


@dataclass(kw_only=True)
class Flow:
    """схема потока одной операции составного узла"""
    nodes: list[FlowNode]
    result: Source


@dataclass(kw_only=True)
class Design:
    """разложение составного узла"""
    node: NodeId
    children: list[NodeCard]
    types: TypeDefs
    flows: dict[str, Flow]
    objection: str | None = None


@dataclass(kw_only=True)
class MapAnswer:
    """ответ задачи «К карта» (LOGIC §8.1) — текст карты с разделами {#id}, карточка корня, типы корня"""
    map_text: str
    card: NodeCard
    types: TypeDefs


@dataclass(kw_only=True)
class Evidence:
    """результат одной проверки; время проверки пишет оболочка, ядро часов не видит"""
    check: Check
    subject: str
    subject_hash: Sha
    hard: bool
    verdict: Verdict
    details: Json
    counterexample: Json | None = None
    tool: str
    trusted: bool


@dataclass(kw_only=True)
class Report:
    """отчёт о нарушении для починки — самодостаточен, прежний ответ не нужен (LOGIC §8.4)"""
    subject: str
    layer: Check
    rule: str
    where: str
    fragment: str | None = None
    expected: str
    counterexample: Json | None = None
    means: str


@dataclass(kw_only=True)
class Acceptance:
    """принят ли предмет и каких доказательств не хватает"""
    accepted: bool
    missing: Checks


@dataclass(kw_only=True)
class Price:
    """цены за миллион токенов"""
    input: Decimal
    output: Decimal
    cache: Decimal | None = None


@dataclass(kw_only=True)
class Operator:
    """профиль оператора — модель, адаптер, настройки, версия подсказок"""
    id: str
    provider: str
    model: str
    base_url: str | None = None
    output_mode: str
    steps: str
    prices: Price
    params: Json | None = None
    prompt_version: str


@dataclass(kw_only=True)
class Limits:
    """пределы проекта; z3_rlimit — детерминированный предел решателя вместо тайм-аута"""
    max_depth: int
    max_children: int
    final_max_ops: int
    final_max_lines: int
    max_complexity: int
    k_lists: int
    z3_rlimit: int
    hypothesis_examples: int


@dataclass(kw_only=True)
class Roles:
    """лестницы операторов по ролям, от дешёвого к сильному"""
    architect: list[str]
    designer: list[str]
    implementer: list[str]


@dataclass(kw_only=True)
class Routing:
    """правила маршрутизации (LOGIC §6.4–§6.8)"""
    target: float
    n_min: int
    prior_bands: RoutingPriorBands
    adapt: bool
    explore: float


@dataclass(kw_only=True)
class RepairPolicy:
    """попытки починки (LOGIC §7.3)"""
    per_rung: int
    form_retries: int


@dataclass(kw_only=True)
class PolicyNode:
    """узел политики — CALL, CHECK, SEQ, PAR, SWITCH, BUDGET, STOP; циклов и рекурсии нет, иначе нет статической оценки стоимости"""
    op: str
    operator: str | None = None
    wording: str | None = None
    with_report: bool | None = None
    children: list[PolicyNode] | None = None
    obs: Observable | None = None
    cases: dict[str, PolicyNode] | None = None
    default: PolicyNode | None = None
    limit_tokens: int | None = None
    child: PolicyNode | None = None
    reason: str | None = None


@dataclass(kw_only=True)
class Policy:
    """политика роли — генотип; данные, а не код; выбирается по журналу повтором без токенов"""
    policy_id: str
    root: PolicyNode


@dataclass(kw_only=True)
class LeafContract:
    """договор операции листа для Э1 (LOGIC §5) — decisions — договорное число решений, объявленное до кода; sequence — прямолинейные шаги, которых требует договор"""
    decisions: int | None = None
    sequence: int | None = None


@dataclass(kw_only=True)
class Config:
    """настройки проекта из project.yaml; trusted — проверки, прошедшие свои контрольные случаи при запуске, его заполняет оболочка по selftest (нет поля — доверенных нет)"""
    limits: Limits
    roles: Roles
    operators: dict[str, Operator]
    routing: Routing
    repair: RepairPolicy
    overrides: dict[str, Override]
    policies: dict[str, Policy] | None = None
    contracts: dict[str, LeafContract] | None = None
    trusted: Checks | None = None


@dataclass(kw_only=True)
class Cell:
    """клетка таблицы компетенций"""
    operator: str
    class_: WorkClass = field(metadata={"json": 'class'})
    n_fit: int
    ok_fit: int
    n_check: int
    ok_check: int
    cost_per_success: Decimal
    low_data: bool


@dataclass(kw_only=True)
class Competence:
    """таблица компетенций; g0 — у разных родов разные победители"""
    cells: list[Cell]
    g0: bool


@dataclass(kw_only=True)
class Candidate:
    """готовая к работе задача до выбора оператора"""
    subject: Subject
    kind: ElementKind
    role: Role
    class_: WorkClass = field(metadata={"json": 'class'})
    prior: int
    level: int


@dataclass(kw_only=True)
class Assignment:
    """назначение оператора и источник решения"""
    subject: Subject
    role: Role
    class_: WorkClass = field(metadata={"json": 'class'})
    operator: str
    rung: int
    decided_by: str


@dataclass(kw_only=True)
class Budget:
    """бюджет проекта в деньгах"""
    limit: Decimal
    spent: Decimal


@dataclass(kw_only=True)
class Element:
    """элемент работы и его история, нужная для эскалации, раннего подозрения и остановок; tokens и cost — расход элемента (BUDGET, tokens_bucket, строка исходов LOGIC §6.8); versions — хэши принятых версий разложения (колебание, §7.8); round — сколько раз владелец оставил карточку (повтор состояния, §7.8)"""
    subject: Subject
    kind: ElementKind
    state: ElementState
    assignment: Assignment | None = None
    attempts: int
    form_retries: int
    reports: list[Report]
    answer_hashes: list[Sha]
    policy_path: str | None = None
    last_subtype: ViolationSubtype | None = None
    tokens: int | None = None
    cost: Decimal | None = None
    versions: list[Sha] | None = None
    round: int | None = None


@dataclass(kw_only=True)
class State:
    """состояние проекта — всё, что восстанавливается из журнала"""
    phase: Phase
    idea: str
    map_text: str
    cards: dict[str, NodeCard]
    designs: dict[str, Design]
    types: dict[str, TypeDef]
    code: dict[str, str]
    evidence: dict[str, Evidences]
    elements: dict[str, Element]
    approvals: dict[str, Sha]
    user_examples: dict[str, list[Example]]
    budget: Budget


@dataclass(kw_only=True)
class Task:
    """работа для одного вызова модели"""
    subject: Subject
    kind: str
    role: Role
    operator: str
    attempt: int
    wording: str
    report: Report | None = None


@dataclass(kw_only=True)
class Action:
    """что оболочка делает дальше"""
    kind: str
    task: Task | None = None
    target: BuildTarget | None = None
    run: str | None = None
    question: Json | None = None
    reason: str | None = None


@dataclass(kw_only=True)
class RawAnswer:
    """ответ модели после разбора конверта поставщика"""
    text: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    finish_reason: str
    refusal: bool


@dataclass(kw_only=True)
class Answer:
    """ответ модели после извлечения — вид, предмет, узел, извлечённое значение (карта, разложение) или код функции; ok — удалось ли извлечь, иначе error — почему; truncated — ответ оборван пределом длины, это не ошибка модели. С 30.09.2026 тип корня (был в rptg.check) — его читает plan, чтобы записать принятое в состояние"""
    ok: bool
    kind: str
    subject: str
    node: str
    op: str | None = None
    value: Json | None = None
    code: str | None = None
    truncated: bool
    error: str | None = None


@dataclass(kw_only=True)
class SandboxOutput:
    """итог прогона в песочнице; report — структурный отчёт, который пишет сгенерированный прогонщик"""
    exit_code: int
    timed_out: bool
    report: Json
    stderr_tail: str | None = None


@dataclass(kw_only=True)
class Event:
    """событие от оболочки"""
    kind: str
    task: Task | None = None
    answer: RawAnswer | None = None
    target: BuildTarget | None = None
    output: SandboxOutput | None = None
    reply: Json | None = None


@dataclass(kw_only=True)
class JournalEntry:
    """запись журнала; метку времени ставит оболочка"""
    kind: str
    subject: str
    data: Json | None = None


@dataclass(kw_only=True)
class Transition:
    """итог события — новое состояние, доказательства, записи журнала"""
    state: State
    evidence: Evidences
    journal: list[JournalEntry]


@dataclass(kw_only=True)
class Prompt:
    """подсказка — устойчивый префикс роли, тело задачи, схема ответа"""
    prefix: str
    body: str
    version: str
    answer_schema: Json
    cache_key: Sha


@dataclass(kw_only=True)
class ProviderRequest:
    """запрос поставщику без ключей — ключи добавляет оболочка"""
    provider: str
    operator: str
    mode: str
    endpoint: str | None = None
    payload: Json


@dataclass(kw_only=True)
class BuildTarget:
    """что собрать"""
    kind: str
    subject: str


@dataclass(kw_only=True)
class FileSet:
    """файлы — путь → текст"""
    files: StrMap


@dataclass(kw_only=True)
class TypeEnv:
    """окружение типов — схемы по именам и типы переменных"""
    types: dict[str, Json]
    vars: StrMap


@dataclass(kw_only=True)
class EnvResult:
    """построенное окружение"""
    ok: bool
    env: TypeEnv
    errors: Strings


@dataclass(kw_only=True)
class ClInfo:
    """разбор, типизация и меры условия (LOGIC §4.5)"""
    ok: bool
    errors: Strings
    type: str
    nodes: int
    quant: int
    nonlin: int
    arith: bool
    strings: bool
    names: Strings


@dataclass(kw_only=True)
class EvalResult:
    """значение условия на данных; деление на ноль даёт ложь, а не ошибку"""
    ok: bool
    value: bool
    error: str | None = None


@dataclass(kw_only=True)
class Proof:
    """итог доказательства F ⇒ цель для списков длины до bound"""
    verdict: str
    counterexample: Json | None = None
    bound: int


@dataclass(kw_only=True)
class Sat:
    """выполнимость набора условий; core — номера строк противоречивого поднабора"""
    verdict: str
    core: list[int]


@dataclass(kw_only=True)
class SubResult:
    """тип a — подтип b; witness — значение, проходящее a и не проходящее b"""
    ok: bool
    witness: Json | None = None


@dataclass(kw_only=True)
class PathType:
    """тип значения по пути внутри типа"""
    ok: bool
    name: str | None = None
    schema: Json
    error: str | None = None


@dataclass(kw_only=True)
class Validation:
    """итог проверки значения по типу"""
    ok: bool
    errors: Strings


@dataclass(kw_only=True)
class ReferenceItem:
    """эталонная задача калибровки — финальный узел с одной операцией и скрытыми тестами"""
    id: str
    class_: WorkClass = field(metadata={"json": 'class'})
    card: NodeCard
    hidden_tests: Json


@dataclass(kw_only=True)
class ReferenceSet:
    """эталонный набор"""
    name: str
    items: list[ReferenceItem]


@dataclass(kw_only=True)
class CalibrationPlan:
    """раздел набора на подбор и проверку и задачи — каждый оператор на каждой задаче"""
    fit: Strings
    check: Strings
    tasks: list[Task]


@dataclass(kw_only=True)
class CalibrationResult:
    """итог одной задачи калибровки"""
    item: str
    class_: WorkClass = field(metadata={"json": 'class'})
    operator: str
    passed: bool
    cost: Decimal
    finish_reason: str


@dataclass(kw_only=True)
class ControlCase:
    """контрольный случай проверки с известным вердиктом"""
    id: str
    check: Check
    input: Json
    expected: Verdict


@dataclass(kw_only=True)
class CaseResult:
    """итог контрольного случая"""
    id: str
    check: Check
    expected: Verdict
    actual: Verdict
    ok: bool


@dataclass(kw_only=True)
class SelftestReport:
    """сводка по проверкам — недоверенная проверка не даёт HARD-доказательств"""
    checks: list[SelftestReportChecksItem]


@dataclass(kw_only=True)
class ViewQuery:
    """запрос представления"""
    kind: str
    subject: str | None = None


@dataclass(kw_only=True)
class View:
    """представление для окна и командной строки"""
    kind: str
    data: Json


@dataclass(kw_only=True)
class RoutingPriorBands:
    designer: list[int]
    implementer: list[int]


@dataclass(kw_only=True)
class SelftestReportChecksItem:
    check: Check
    passed: int
    failed: int
    trusted: bool
    failures: Strings


NodeId = str
"""путь узла от корня через точку"""

OpRef = str
"""операция — узел:операция"""

Subject = str
"""предмет работы — вид:узел или вид:узел:операция"""

Cl = str
"""текст условия на языке CL"""

Sha = str
"""SHA-256 канонической записи, шестнадцатерично"""

Decimal = str
"""десятичное число записью"""

Json = Any
"""непрозрачное значение JSON"""

Strings = list[str]
"""список строк"""

StrMap = dict[str, str]
"""словарь строка → строка"""

Effect = str
"""объявленный эффект операции"""

Role = str
"""роль в конвейере"""

WorkClass = str
"""класс работы для маршрутизации (LOGIC §6.3)"""

Check = str
"""слой проверки"""

Checks = list[Check]
"""список слоёв"""

Verdict = str
"""вердикт проверки"""

Phase = str
"""фаза проекта (LOGIC §7.1)"""

ElementKind = str
"""вид элемента работы"""

ElementState = str
"""состояние элемента (LOGIC §7.2)"""

Params = list[Param]
"""список параметров"""

TypeDefs = list[TypeDef]
"""список типов"""

Source = Any
"""источник значения — путь строкой или литерал {const}"""

Evidences = list[Evidence]
"""список доказательств в порядке слоёв P1 P2 P3 P4 P5 P7 E1 E2 E3 E6"""

Observable = str
"""наблюдаемая величина политики — закрытый список, считается механически по элементу (arch2 SPEC §1.2)"""

ViolationSubtype = str
"""подтип нарушения — ось, по которой в опытах различались барьеры (arch2 REPORT §2.3)"""

Candidates = list[Candidate]
"""список кандидатов в порядке очереди"""

Assignments = list[Assignment]
"""список назначений"""

Cls = list[Cl]
"""список условий"""

CalibrationResults = list[CalibrationResult]
"""итоги калибровки"""

ControlCases = list[ControlCase]
"""набор контрольных случаев"""

CaseResults = list[CaseResult]
"""итоги контрольных случаев"""


SCHEMAS: dict[str, Any] = {
    'NodeId': {'type': 'string', 'pattern': '^[a-z_][a-z0-9_]*(\\.[a-z_][a-z0-9_]*)*$'},
    'OpRef': {'type': 'string', 'pattern': '^[a-z_][a-z0-9_]*(\\.[a-z_][a-z0-9_]*)*:[a-z_][a-z0-9_]*$'},
    'Subject': {'type': 'string', 'pattern': '^(map|design|function|assembly):[a-z_][a-z0-9_.]*(:[a-z_][a-z0-9_]*)?$'},
    'Cl': {'type': 'string', 'minLength': 1},
    'Sha': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
    'Decimal': {'type': 'string', 'pattern': '^-?[0-9]+(\\.[0-9]+)?$'},
    'Json': {},
    'Strings': {'type': 'array', 'items': {'type': 'string'}},
    'StrMap': {'type': 'object', 'additionalProperties': {'type': 'string'}},
    'Effect': {'type': 'string', 'enum': ['fs.read', 'fs.write', 'stdout', 'clock', 'random']},
    'Role': {'type': 'string', 'enum': ['architect', 'designer', 'implementer']},
    'WorkClass': {'type': 'string', 'enum': ['map', 'design', 'io', 'compute', 'search', 'text', 'transform']},
    'Check': {'type': 'string', 'enum': ['P1', 'P2', 'P3', 'P4', 'P5', 'P7', 'E1', 'E2', 'E3', 'E6']},
    'Checks': {'type': 'array', 'items': {'$ref': 'Check'}},
    'Verdict': {'type': 'string', 'enum': ['pass', 'fail', 'unknown']},
    'Phase': {'type': 'string', 'enum': ['NEW', 'MAP', 'MAP_CHECK', 'MAP_REVIEW', 'DESIGN', 'BUILD', 'E2E', 'DONE', 'PAUSED']},
    'ElementKind': {'type': 'string', 'enum': ['map', 'design', 'function', 'assembly']},
    'ElementState': {'type': 'string', 'enum': ['planned', 'writing', 'checking', 'approval', 'form_retry', 'repairing', 'escalated', 'promoted', 'card_suspect', 'accepted', 'stale']},
    'Example': {'type': 'object', 'required': ['in', 'out', 'source'], 'properties': {'in': {'$ref': 'Json'}, 'out': {'$ref': 'Json'}, 'source': {'type': 'string', 'enum': ['user', 'model']}, 'match': {'type': 'string', 'enum': ['exact', 'subset']}}},
    'Param': {'type': 'object', 'required': ['name', 'type'], 'properties': {'name': {'type': 'string'}, 'type': {'type': 'string'}}},
    'Params': {'type': 'array', 'items': {'$ref': 'Param'}},
    'Op': {'type': 'object', 'required': ['name', 'doc', 'params', 'result', 'requires', 'ensures', 'effects', 'examples'], 'properties': {'name': {'type': 'string', 'pattern': '^[a-z_][a-z0-9_]*$'}, 'doc': {'type': 'string'}, 'params': {'$ref': 'Params'}, 'result': {'type': 'string'}, 'requires': {'type': 'array', 'items': {'$ref': 'Cl'}}, 'ensures': {'type': 'array', 'items': {'$ref': 'Cl'}}, 'effects': {'type': 'array', 'items': {'$ref': 'Effect'}}, 'examples': {'type': 'array', 'items': {'$ref': 'Example'}}}},
    'Override': {'type': 'object', 'properties': {'kind': {'type': 'string', 'enum': ['final', 'composite']}, 'designer': {'type': 'string'}, 'implementer': {'type': 'string'}, 'start_rung': {'type': 'integer', 'minimum': 1}, 'max_rung': {'type': 'integer', 'minimum': 1}, 'approve': {'type': 'boolean'}, 'steps': {'type': 'string', 'enum': ['combined', 'split']}, 'est_lines': {'type': 'integer', 'minimum': 1}, 'max_lines': {'type': 'integer', 'minimum': 1}, 'max_complexity': {'type': 'integer', 'minimum': 1}}},
    'NodeCard': {'type': 'object', 'required': ['id', 'owner', 'purpose', 'uses', 'effects', 'allowed_imports', 'est_lines', 'ops'], 'properties': {'id': {'$ref': 'NodeId'}, 'parent': {'$ref': 'NodeId'}, 'owner': {'$ref': 'NodeId'}, 'purpose': {'type': 'string'}, 'uses': {'type': 'array', 'items': {'$ref': 'NodeId'}}, 'effects': {'type': 'array', 'items': {'$ref': 'Effect'}}, 'allowed_imports': {'type': 'array', 'items': {'type': 'string'}}, 'est_lines': {'type': 'integer', 'minimum': 1}, 'ops': {'type': 'array', 'items': {'$ref': 'Op'}, 'minItems': 1}}},
    'TypeDef': {'type': 'object', 'required': ['name', 'owner', 'schema'], 'properties': {'name': {'type': 'string'}, 'owner': {'$ref': 'NodeId'}, 'doc': {'type': 'string'}, 'schema': {'$ref': 'Json'}}},
    'TypeDefs': {'type': 'array', 'items': {'$ref': 'TypeDef'}},
    'Source': {'oneOf': [{'type': 'string', 'minLength': 1}, {'type': 'object', 'required': ['const'], 'properties': {'const': {'$ref': 'Json'}}}]},
    'FlowNode': {'type': 'object', 'required': ['id'], 'properties': {'id': {'type': 'string'}, 'call': {'type': 'string'}, 'map': {'type': 'string'}, 'fold': {'type': 'string'}, 'record': {'type': 'string'}, 'over': {'$ref': 'Source'}, 'init': {'$ref': 'Source'}, 'acc': {'type': 'string'}, 'item': {'type': 'string'}, 'args': {'type': 'object', 'additionalProperties': {'$ref': 'Source'}}, 'fields': {'type': 'object', 'additionalProperties': {'$ref': 'Source'}}}},
    'Flow': {'type': 'object', 'required': ['nodes', 'result'], 'properties': {'nodes': {'type': 'array', 'items': {'$ref': 'FlowNode'}}, 'result': {'$ref': 'Source'}}},
    'Design': {'type': 'object', 'required': ['node', 'children', 'types', 'flows'], 'properties': {'node': {'$ref': 'NodeId'}, 'children': {'type': 'array', 'items': {'$ref': 'NodeCard'}}, 'types': {'$ref': 'TypeDefs'}, 'flows': {'type': 'object', 'additionalProperties': {'$ref': 'Flow'}}, 'objection': {'type': 'string'}}},
    'MapAnswer': {'type': 'object', 'required': ['map_text', 'card', 'types'], 'properties': {'map_text': {'type': 'string'}, 'card': {'$ref': 'NodeCard'}, 'types': {'$ref': 'TypeDefs'}}},
    'Evidence': {'type': 'object', 'required': ['check', 'subject', 'subject_hash', 'hard', 'verdict', 'details', 'tool', 'trusted'], 'properties': {'check': {'$ref': 'Check'}, 'subject': {'type': 'string'}, 'subject_hash': {'$ref': 'Sha'}, 'hard': {'type': 'boolean'}, 'verdict': {'$ref': 'Verdict'}, 'details': {'$ref': 'Json'}, 'counterexample': {'$ref': 'Json'}, 'tool': {'type': 'string'}, 'trusted': {'type': 'boolean'}}},
    'Evidences': {'type': 'array', 'items': {'$ref': 'Evidence'}},
    'Report': {'type': 'object', 'required': ['subject', 'layer', 'rule', 'where', 'expected', 'means'], 'properties': {'subject': {'type': 'string'}, 'layer': {'$ref': 'Check'}, 'rule': {'type': 'string'}, 'where': {'type': 'string'}, 'fragment': {'type': 'string'}, 'expected': {'type': 'string'}, 'counterexample': {'$ref': 'Json'}, 'means': {'type': 'string'}}},
    'Acceptance': {'type': 'object', 'required': ['accepted', 'missing'], 'properties': {'accepted': {'type': 'boolean'}, 'missing': {'$ref': 'Checks'}}},
    'Price': {'type': 'object', 'required': ['input', 'output'], 'properties': {'input': {'$ref': 'Decimal'}, 'output': {'$ref': 'Decimal'}, 'cache': {'$ref': 'Decimal'}}},
    'Operator': {'type': 'object', 'required': ['id', 'provider', 'model', 'output_mode', 'steps', 'prices', 'prompt_version'], 'properties': {'id': {'type': 'string'}, 'provider': {'type': 'string', 'enum': ['anthropic', 'openai', 'google', 'openrouter', 'openai_compatible', 'llamacpp']}, 'model': {'type': 'string'}, 'base_url': {'type': 'string'}, 'output_mode': {'type': 'string', 'enum': ['json_schema', 'tool', 'grammar', 'prompt']}, 'steps': {'type': 'string', 'enum': ['combined', 'split']}, 'prices': {'$ref': 'Price'}, 'params': {'$ref': 'Json'}, 'prompt_version': {'type': 'string'}}},
    'Limits': {'type': 'object', 'required': ['max_depth', 'max_children', 'final_max_ops', 'final_max_lines', 'max_complexity', 'k_lists', 'z3_rlimit', 'hypothesis_examples'], 'properties': {'max_depth': {'type': 'integer', 'minimum': 1}, 'max_children': {'type': 'integer', 'minimum': 1}, 'final_max_ops': {'type': 'integer', 'minimum': 1}, 'final_max_lines': {'type': 'integer', 'minimum': 1}, 'max_complexity': {'type': 'integer', 'minimum': 1}, 'k_lists': {'type': 'integer', 'minimum': 1}, 'z3_rlimit': {'type': 'integer', 'minimum': 1}, 'hypothesis_examples': {'type': 'integer', 'minimum': 1}}},
    'Roles': {'type': 'object', 'required': ['architect', 'designer', 'implementer'], 'properties': {'architect': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1}, 'designer': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1}, 'implementer': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1}}},
    'Routing': {'type': 'object', 'required': ['target', 'n_min', 'prior_bands', 'adapt', 'explore'], 'properties': {'target': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'n_min': {'type': 'integer', 'minimum': 1}, 'prior_bands': {'type': 'object', 'required': ['designer', 'implementer'], 'properties': {'designer': {'type': 'array', 'items': {'type': 'integer'}}, 'implementer': {'type': 'array', 'items': {'type': 'integer'}}}}, 'adapt': {'type': 'boolean'}, 'explore': {'type': 'number', 'minimum': 0, 'maximum': 1}}},
    'RepairPolicy': {'type': 'object', 'required': ['per_rung', 'form_retries'], 'properties': {'per_rung': {'type': 'integer', 'minimum': 0}, 'form_retries': {'type': 'integer', 'minimum': 0}}},
    'Observable': {'type': 'string', 'enum': ['violation_subtype', 'same_failure', 'attempts_used', 'work_class', 'tokens_bucket']},
    'ViolationSubtype': {'type': 'string', 'enum': ['none', 'form', 'contract', 'dependency', 'semantic', 'value', 'other']},
    'PolicyNode': {'type': 'object', 'required': ['op'], 'properties': {'op': {'type': 'string', 'enum': ['CALL', 'CHECK', 'SEQ', 'PAR', 'SWITCH', 'BUDGET', 'STOP']}, 'operator': {'type': 'string'}, 'wording': {'type': 'string', 'enum': ['primary', 'alternative']}, 'with_report': {'type': 'boolean'}, 'children': {'type': 'array', 'items': {'$ref': 'PolicyNode'}}, 'obs': {'$ref': 'Observable'}, 'cases': {'type': 'object', 'additionalProperties': {'$ref': 'PolicyNode'}}, 'default': {'$ref': 'PolicyNode'}, 'limit_tokens': {'type': 'integer', 'minimum': 1}, 'child': {'$ref': 'PolicyNode'}, 'reason': {'type': 'string'}}},
    'Policy': {'type': 'object', 'required': ['policy_id', 'root'], 'properties': {'policy_id': {'type': 'string'}, 'root': {'$ref': 'PolicyNode'}}},
    'LeafContract': {'type': 'object', 'properties': {'decisions': {'type': 'integer', 'minimum': 0}, 'sequence': {'type': 'integer', 'minimum': 0}}},
    'Config': {'type': 'object', 'required': ['limits', 'roles', 'operators', 'routing', 'repair', 'overrides'], 'properties': {'limits': {'$ref': 'Limits'}, 'roles': {'$ref': 'Roles'}, 'operators': {'type': 'object', 'additionalProperties': {'$ref': 'Operator'}}, 'routing': {'$ref': 'Routing'}, 'repair': {'$ref': 'RepairPolicy'}, 'overrides': {'type': 'object', 'additionalProperties': {'$ref': 'Override'}}, 'policies': {'type': 'object', 'additionalProperties': {'$ref': 'Policy'}}, 'contracts': {'type': 'object', 'additionalProperties': {'$ref': 'LeafContract'}}, 'trusted': {'$ref': 'Checks'}}},
    'Cell': {'type': 'object', 'required': ['operator', 'class', 'n_fit', 'ok_fit', 'n_check', 'ok_check', 'cost_per_success', 'low_data'], 'properties': {'operator': {'type': 'string'}, 'class': {'$ref': 'WorkClass'}, 'n_fit': {'type': 'integer', 'minimum': 0}, 'ok_fit': {'type': 'integer', 'minimum': 0}, 'n_check': {'type': 'integer', 'minimum': 0}, 'ok_check': {'type': 'integer', 'minimum': 0}, 'cost_per_success': {'$ref': 'Decimal'}, 'low_data': {'type': 'boolean'}}},
    'Competence': {'type': 'object', 'required': ['cells', 'g0'], 'properties': {'cells': {'type': 'array', 'items': {'$ref': 'Cell'}}, 'g0': {'type': 'boolean'}}},
    'Candidate': {'type': 'object', 'required': ['subject', 'kind', 'role', 'class', 'prior', 'level'], 'properties': {'subject': {'$ref': 'Subject'}, 'kind': {'$ref': 'ElementKind'}, 'role': {'$ref': 'Role'}, 'class': {'$ref': 'WorkClass'}, 'prior': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'level': {'type': 'integer', 'minimum': 1}}},
    'Candidates': {'type': 'array', 'items': {'$ref': 'Candidate'}},
    'Assignment': {'type': 'object', 'required': ['subject', 'role', 'class', 'operator', 'rung', 'decided_by'], 'properties': {'subject': {'$ref': 'Subject'}, 'role': {'$ref': 'Role'}, 'class': {'$ref': 'WorkClass'}, 'operator': {'type': 'string'}, 'rung': {'type': 'integer', 'minimum': 1}, 'decided_by': {'type': 'string', 'enum': ['rule', 'manual', 'table', 'prior', 'adapt', 'promotion']}}},
    'Assignments': {'type': 'array', 'items': {'$ref': 'Assignment'}},
    'Budget': {'type': 'object', 'required': ['limit', 'spent'], 'properties': {'limit': {'$ref': 'Decimal'}, 'spent': {'$ref': 'Decimal'}}},
    'Element': {'type': 'object', 'required': ['subject', 'kind', 'state', 'attempts', 'form_retries', 'reports', 'answer_hashes'], 'properties': {'subject': {'$ref': 'Subject'}, 'kind': {'$ref': 'ElementKind'}, 'state': {'$ref': 'ElementState'}, 'assignment': {'$ref': 'Assignment'}, 'attempts': {'type': 'integer', 'minimum': 0}, 'form_retries': {'type': 'integer', 'minimum': 0}, 'reports': {'type': 'array', 'items': {'$ref': 'Report'}}, 'answer_hashes': {'type': 'array', 'items': {'$ref': 'Sha'}}, 'policy_path': {'type': 'string'}, 'last_subtype': {'$ref': 'ViolationSubtype'}, 'tokens': {'type': 'integer', 'minimum': 0}, 'cost': {'$ref': 'Decimal'}, 'versions': {'type': 'array', 'items': {'$ref': 'Sha'}}, 'round': {'type': 'integer', 'minimum': 0}}},
    'State': {'type': 'object', 'required': ['phase', 'idea', 'map_text', 'cards', 'designs', 'types', 'code', 'evidence', 'elements', 'approvals', 'user_examples', 'budget'], 'properties': {'phase': {'$ref': 'Phase'}, 'idea': {'type': 'string'}, 'map_text': {'type': 'string'}, 'cards': {'type': 'object', 'additionalProperties': {'$ref': 'NodeCard'}}, 'designs': {'type': 'object', 'additionalProperties': {'$ref': 'Design'}}, 'types': {'type': 'object', 'additionalProperties': {'$ref': 'TypeDef'}}, 'code': {'type': 'object', 'additionalProperties': {'type': 'string'}}, 'evidence': {'type': 'object', 'additionalProperties': {'$ref': 'Evidences'}}, 'elements': {'type': 'object', 'additionalProperties': {'$ref': 'Element'}}, 'approvals': {'type': 'object', 'additionalProperties': {'$ref': 'Sha'}}, 'user_examples': {'type': 'object', 'additionalProperties': {'type': 'array', 'items': {'$ref': 'Example'}}}, 'budget': {'$ref': 'Budget'}}},
    'Task': {'type': 'object', 'required': ['subject', 'kind', 'role', 'operator', 'attempt', 'wording'], 'properties': {'subject': {'$ref': 'Subject'}, 'kind': {'type': 'string', 'enum': ['map', 'design', 'design_r1', 'design_r2', 'design_r3', 'function', 'revision']}, 'role': {'$ref': 'Role'}, 'operator': {'type': 'string'}, 'attempt': {'type': 'integer', 'minimum': 1}, 'wording': {'type': 'string', 'enum': ['primary', 'alternative']}, 'report': {'$ref': 'Report'}}},
    'Action': {'type': 'object', 'required': ['kind'], 'properties': {'kind': {'type': 'string', 'enum': ['call_model', 'run_sandbox', 'ask_user', 'pause', 'stop']}, 'task': {'$ref': 'Task'}, 'target': {'$ref': 'BuildTarget'}, 'run': {'type': 'string', 'enum': ['e1_mypy', 'e2_e3', 'e6', 'smoke']}, 'question': {'$ref': 'Json'}, 'reason': {'type': 'string'}}},
    'RawAnswer': {'type': 'object', 'required': ['text', 'input_tokens', 'output_tokens', 'cache_read_tokens', 'finish_reason', 'refusal'], 'properties': {'text': {'type': 'string'}, 'input_tokens': {'type': 'integer', 'minimum': 0}, 'output_tokens': {'type': 'integer', 'minimum': 0}, 'cache_read_tokens': {'type': 'integer', 'minimum': 0}, 'finish_reason': {'type': 'string'}, 'refusal': {'type': 'boolean'}}},
    'Answer': {'type': 'object', 'required': ['ok', 'kind', 'subject', 'node', 'truncated'], 'properties': {'ok': {'type': 'boolean'}, 'kind': {'type': 'string', 'enum': ['map', 'design', 'design_step', 'function', 'none']}, 'subject': {'type': 'string'}, 'node': {'type': 'string'}, 'op': {'type': 'string'}, 'value': {'$ref': 'Json'}, 'code': {'type': 'string'}, 'truncated': {'type': 'boolean'}, 'error': {'type': 'string'}}},
    'SandboxOutput': {'type': 'object', 'required': ['exit_code', 'timed_out', 'report'], 'properties': {'exit_code': {'type': 'integer'}, 'timed_out': {'type': 'boolean'}, 'report': {'$ref': 'Json'}, 'stderr_tail': {'type': 'string'}}},
    'Event': {'type': 'object', 'required': ['kind'], 'properties': {'kind': {'type': 'string', 'enum': ['model_answered', 'sandbox_finished', 'user_answered', 'command']}, 'task': {'$ref': 'Task'}, 'answer': {'$ref': 'RawAnswer'}, 'target': {'$ref': 'BuildTarget'}, 'output': {'$ref': 'SandboxOutput'}, 'reply': {'$ref': 'Json'}}},
    'JournalEntry': {'type': 'object', 'required': ['kind', 'subject'], 'properties': {'kind': {'type': 'string'}, 'subject': {'type': 'string'}, 'data': {'$ref': 'Json'}}},
    'Transition': {'type': 'object', 'required': ['state', 'evidence', 'journal'], 'properties': {'state': {'$ref': 'State'}, 'evidence': {'$ref': 'Evidences'}, 'journal': {'type': 'array', 'items': {'$ref': 'JournalEntry'}}}},
    'Prompt': {'type': 'object', 'required': ['prefix', 'body', 'version', 'answer_schema', 'cache_key'], 'properties': {'prefix': {'type': 'string'}, 'body': {'type': 'string'}, 'version': {'type': 'string'}, 'answer_schema': {'$ref': 'Json'}, 'cache_key': {'$ref': 'Sha'}}},
    'ProviderRequest': {'type': 'object', 'required': ['provider', 'operator', 'mode', 'payload'], 'properties': {'provider': {'type': 'string'}, 'operator': {'type': 'string'}, 'mode': {'type': 'string', 'enum': ['json_schema', 'tool', 'grammar', 'prompt']}, 'endpoint': {'type': 'string'}, 'payload': {'$ref': 'Json'}}},
    'BuildTarget': {'type': 'object', 'required': ['kind', 'subject'], 'properties': {'kind': {'type': 'string', 'enum': ['function_tests', 'node_package', 'program']}, 'subject': {'type': 'string'}}},
    'FileSet': {'type': 'object', 'required': ['files'], 'properties': {'files': {'$ref': 'StrMap'}}},
    'Cls': {'type': 'array', 'items': {'$ref': 'Cl'}},
    'TypeEnv': {'type': 'object', 'required': ['types', 'vars'], 'properties': {'types': {'type': 'object', 'additionalProperties': {'$ref': 'Json'}}, 'vars': {'$ref': 'StrMap'}}},
    'EnvResult': {'type': 'object', 'required': ['ok', 'env', 'errors'], 'properties': {'ok': {'type': 'boolean'}, 'env': {'$ref': 'TypeEnv'}, 'errors': {'$ref': 'Strings'}}},
    'ClInfo': {'type': 'object', 'required': ['ok', 'errors', 'type', 'nodes', 'quant', 'nonlin', 'arith', 'strings', 'names'], 'properties': {'ok': {'type': 'boolean'}, 'errors': {'$ref': 'Strings'}, 'type': {'type': 'string'}, 'nodes': {'type': 'integer', 'minimum': 0}, 'quant': {'type': 'integer', 'minimum': 0}, 'nonlin': {'type': 'integer', 'minimum': 0}, 'arith': {'type': 'boolean'}, 'strings': {'type': 'boolean'}, 'names': {'$ref': 'Strings'}}},
    'EvalResult': {'type': 'object', 'required': ['ok', 'value'], 'properties': {'ok': {'type': 'boolean'}, 'value': {'type': 'boolean'}, 'error': {'type': 'string'}}},
    'Proof': {'type': 'object', 'required': ['verdict', 'bound'], 'properties': {'verdict': {'type': 'string', 'enum': ['proved', 'refuted', 'unknown']}, 'counterexample': {'$ref': 'Json'}, 'bound': {'type': 'integer', 'minimum': 1}}},
    'Sat': {'type': 'object', 'required': ['verdict', 'core'], 'properties': {'verdict': {'type': 'string', 'enum': ['sat', 'unsat', 'unknown']}, 'core': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}}}},
    'SubResult': {'type': 'object', 'required': ['ok'], 'properties': {'ok': {'type': 'boolean'}, 'witness': {'$ref': 'Json'}}},
    'PathType': {'type': 'object', 'required': ['ok', 'schema'], 'properties': {'ok': {'type': 'boolean'}, 'name': {'type': 'string'}, 'schema': {'$ref': 'Json'}, 'error': {'type': 'string'}}},
    'Validation': {'type': 'object', 'required': ['ok', 'errors'], 'properties': {'ok': {'type': 'boolean'}, 'errors': {'$ref': 'Strings'}}},
    'ReferenceItem': {'type': 'object', 'required': ['id', 'class', 'card', 'hidden_tests'], 'properties': {'id': {'type': 'string'}, 'class': {'$ref': 'WorkClass'}, 'card': {'$ref': 'NodeCard'}, 'hidden_tests': {'$ref': 'Json'}}},
    'ReferenceSet': {'type': 'object', 'required': ['name', 'items'], 'properties': {'name': {'type': 'string'}, 'items': {'type': 'array', 'items': {'$ref': 'ReferenceItem'}}}},
    'CalibrationPlan': {'type': 'object', 'required': ['fit', 'check', 'tasks'], 'properties': {'fit': {'$ref': 'Strings'}, 'check': {'$ref': 'Strings'}, 'tasks': {'type': 'array', 'items': {'$ref': 'Task'}}}},
    'CalibrationResult': {'type': 'object', 'required': ['item', 'class', 'operator', 'passed', 'cost', 'finish_reason'], 'properties': {'item': {'type': 'string'}, 'class': {'$ref': 'WorkClass'}, 'operator': {'type': 'string'}, 'passed': {'type': 'boolean'}, 'cost': {'$ref': 'Decimal'}, 'finish_reason': {'type': 'string'}}},
    'CalibrationResults': {'type': 'array', 'items': {'$ref': 'CalibrationResult'}},
    'ControlCase': {'type': 'object', 'required': ['id', 'check', 'input', 'expected'], 'properties': {'id': {'type': 'string'}, 'check': {'$ref': 'Check'}, 'input': {'$ref': 'Json'}, 'expected': {'$ref': 'Verdict'}}},
    'ControlCases': {'type': 'array', 'items': {'$ref': 'ControlCase'}},
    'CaseResult': {'type': 'object', 'required': ['id', 'check', 'expected', 'actual', 'ok'], 'properties': {'id': {'type': 'string'}, 'check': {'$ref': 'Check'}, 'expected': {'$ref': 'Verdict'}, 'actual': {'$ref': 'Verdict'}, 'ok': {'type': 'boolean'}}},
    'CaseResults': {'type': 'array', 'items': {'$ref': 'CaseResult'}},
    'SelftestReport': {'type': 'object', 'required': ['checks'], 'properties': {'checks': {'type': 'array', 'items': {'type': 'object', 'required': ['check', 'passed', 'failed', 'trusted', 'failures'], 'properties': {'check': {'$ref': 'Check'}, 'passed': {'type': 'integer', 'minimum': 0}, 'failed': {'type': 'integer', 'minimum': 0}, 'trusted': {'type': 'boolean'}, 'failures': {'$ref': 'Strings'}}}}}},
    'ViewQuery': {'type': 'object', 'required': ['kind'], 'properties': {'kind': {'type': 'string', 'enum': ['status', 'node', 'graph', 'competence']}, 'subject': {'type': 'string'}}},
    'View': {'type': 'object', 'required': ['kind', 'data'], 'properties': {'kind': {'type': 'string'}, 'data': {'$ref': 'Json'}}},
}
"""JSON Schema типов, которыми владеет узел; ссылка на тип — {"$ref": имя}."""
