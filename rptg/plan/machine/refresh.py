"""Лист rptg.plan.machine.refresh — мёртвые операции (LOGIC §7.6) и перепроверка устаревшего без
модели (§7.7): устаревание ≠ ошибка (F37, F38) — разложения и статика функций проверяются заново
через check на сохранённом ответе, прогоны песочницы — позже, модель зовётся только там, где
проверка упала.

Функции приняты по карточке design/rptg.plan.machine.yaml; обвязку пишет скрипт. Состояние, ответы
проверок и отчёты — JSON; каноническую запись разложения для события даёт lang в схеме — модуль json
узлу не разрешён. Снятие мёртвого и чистка типов — две работы, две операции (после Э1 01.10.2026:
в одной функции решений было 49 при допуске 32). Перезапуск элементов без сохранённой версии —
своя операция (после контрольных случаев 01.10.2026): перепроверять у них нечего, а старая позиция
относится к прежней карточке.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Event, JournalEntry, RawAnswer, Task
from rptg.plan._types import Settled
from rptg.plan.machine._types import RecheckJobs, RecheckStored, RecheckTargets

if TYPE_CHECKING:
    from rptg._types import Config, Json, Strings
    from rptg.plan.machine._types import Acceptances


def remove(settled: Settled, dead: Strings, cfg: Config) -> Settled:
    """Фаза DESIGN, все разложения приняты, ни одного на утверждении и под подозрением, мёртвые есть —
    каскадом: операции из карточек, их схемы из разложений; узел без операций — вместе с поддеревом и
    ребёнком в разложении родителя; элементы снятого. Узлы с изменившимися карточками — в changed;
    запись revision со списком; изменилось разложение корня — оно снова на утверждении. Иначе — как
    есть."""
    s, els, gone = settled.state, settled.state["elements"], set(dead)

    def blocked():
        designing = any(e["state"] != "accepted" for k, e in els.items() if k.startswith("design:"))
        waiting = any(e["state"] in ("approval", "card_suspect") for e in els.values())
        return s["phase"] != "DESIGN" or not gone or designing or waiting

    def strip():
        out = {n: {**c, "ops": [o for o in c["ops"] if f"{n}:{o['name']}" not in gone]} for n, c in s["cards"].items()}
        return out, {n for n, c in out.items() if not c["ops"]}

    if blocked():
        return settled
    kept, empty = strip()

    def alive(node):
        return not any(node == e or node.startswith(e + ".") for e in empty)

    def design(n, d):
        return {**d, "children": [cards[c["id"]] for c in d["children"] if c["id"] in cards],
                "flows": {o: fl for o, fl in d["flows"].items() if f"{n}:{o}" not in gone}}

    def left():
        out = {k: e for k, e in els.items() if alive(k.split(":")[1]) and k.partition(":")[2] not in gone}
        root = next((c for c in s["cards"] if "." not in c), "")
        if designs.get(root) != s["designs"].get(root):
            out[f"design:{root}"] = {**out[f"design:{root}"], "state": "approval"}
        return out

    cards = {n: c for n, c in kept.items() if alive(n)}
    designs = {n: design(n, d) for n, d in s["designs"].items() if alive(n)}
    elements = left()
    changed = sorted(set(settled.changed) | {n for n in cards if cards[n] != s["cards"][n]})
    notes = list(settled.notes) + [JournalEntry(kind="revision", subject="dead", data={"removed": sorted(gone)})]
    return Settled(state={**s, "cards": cards, "designs": designs, "elements": elements}, changed=changed, notes=notes)


def types(before: Json, settled: Settled) -> Settled:
    """Типы, на которые ссылались до снятия и не ссылаются после, снимаются; ссылки — типы параметров
    и результатов операций карточек и записи схем разложений, замыканием по $ref схем типов; ничего
    не снято — как есть."""
    def seeds(state):
        todo = [t.strip("[]") for c in state["cards"].values() for o in c["ops"] for t in [p["type"] for p in o["params"]] + [o["result"]]]
        return todo + [n["record"] for d in state["designs"].values() for fl in d["flows"].values() for n in fl["nodes"] if "record" in n]

    def refs(schema):
        out, stack = [], [schema]
        while stack:
            v = stack.pop()
            out += [v["$ref"]] if isinstance(v, dict) and "$ref" in v else []
            stack += list(v.values()) if isinstance(v, dict) else v if isinstance(v, list) else []
        return out

    def used(state):
        todo, found = seeds(state), set()
        while todo:
            name = todo.pop()
            if name in state["types"] and name not in found:
                found.add(name)
                todo += refs(state["types"][name]["schema"])
        return found

    lost = used(before) - used(settled.state)
    if not lost:
        return settled
    s = settled.state
    return Settled(state={**s, "types": {n: t for n, t in s["types"].items() if n not in lost}}, changed=settled.changed,
                   notes=settled.notes)


def restart(settled: Settled) -> Settled:
    """Разложения и функции узлов из changed без сохранённой версии (разложения, кода) начинаются
    заново на новой карточке: planned, без назначения, позиции, отчётов и хэшей ответов — старые
    провалы и повторы относились к прежней карточке; повышенные функции остаются как есть."""
    s = settled.state
    els = dict(s["elements"])
    for subject, e in sorted(els.items()):
        kind, _, rest = subject.partition(":")
        kept = rest in s["designs"] if kind == "design" else rest in s["code"]
        if kind in ("design", "function") and rest.split(":")[0] in settled.changed and not kept and e["state"] != "promoted":
            fresh = {k: v for k, v in e.items() if k != "assignment"}
            els[subject] = {**fresh, "state": "planned", "policy_path": "", "reports": [], "answer_hashes": []}
    return Settled(state={**s, "elements": els}, changed=list(settled.changed), notes=list(settled.notes))


def targets(settled: Settled, stale: Strings) -> RecheckTargets:
    """Предметы перепроверки — устаревшие по check.stale и элементы в stale, без повторов, по порядку;
    снятые и ждущие утверждения пропускаются (их только что проверили, приёмку даёт пользователь);
    сборка — planned (прогон позже); карта с текстом, разложение с сохранённой версией и функция с
    кодом — в предметы, их элементы — stale; значение — карта (текст, карточка и типы корня),
    разложение без поля node, у функции — пустой объект."""
    s = settled.state
    els, subjects, values = dict(s["elements"]), [], []

    def value(kind, rest):
        if kind == "map":
            return {"map_text": s["map_text"], "card": s["cards"][rest], "types": [t for t in s["types"].values() if t["owner"] == rest]}
        return {k: v for k, v in s["designs"][rest].items() if k != "node"} if kind == "design" else {}

    for subject in sorted(set(stale) | {k for k, e in els.items() if e["state"] == "stale"}):
        kind, _, rest = subject.partition(":")
        if subject not in els or els[subject]["state"] == "approval":
            continue
        stored = {"map": bool(s["map_text"]), "design": rest in s["designs"], "function": rest in s["code"]}
        if kind == "assembly":
            els[subject] = {**els[subject], "state": "planned"}
        elif stored.get(kind):
            els[subject] = {**els[subject], "state": "stale"}
            subjects.append(subject)
            values.append(value(kind, rest))
    return RecheckTargets(state={**s, "elements": els}, subjects=subjects, values=values)


def jobs(targets: RecheckTargets, texts: Strings, cfg: Config) -> RecheckJobs:
    """Событие ответа модели на предмет: задача — предмет, вид по предмету, роль и оператор
    назначения элемента (нет — первый лестницы роли), попытка элемента (не меньше 1), primary; ответ —
    у карты и разложения их каноническая запись, у функции код в блоке python; расход нулевой,
    finish_reason recheck."""
    s, events = targets.state, []
    for subject, text in zip(targets.subjects, texts):
        kind, _, rest = subject.partition(":")
        e = s["elements"][subject]
        a = e.get("assignment") or {}
        role = a.get("role") or ("implementer" if kind == "function" else "designer")
        body = f"```python\n{s['code'][rest]}\n```\n" if kind == "function" else text
        events.append(Event(kind="model_answered",
                            task=Task(subject=subject, kind=kind, role=role, operator=a.get("operator") or getattr(cfg.roles, role)[0],
                                      attempt=max(1, e["attempts"]), wording="primary"),
                            answer=RawAnswer(text=body, input_tokens=0, output_tokens=0, cache_read_tokens=0, finish_reason="recheck",
                                             refusal=False)))
    return RecheckJobs(state=s, events=events, subjects=list(targets.subjects))


def store(jobs: RecheckJobs, results: Json) -> RecheckStored:
    """Доказательства каждого события — к его предмету; провалы по порядку."""
    s, evidence, failures = jobs.state, dict(jobs.state["evidence"]), []
    for subject, got in zip(jobs.subjects, results):
        evidence[subject] = evidence.get(subject, []) + list(got)
        failures += [e for e in got if e["verdict"] == "fail"]
    return RecheckStored(state={**s, "evidence": evidence}, failures=failures, subjects=list(jobs.subjects))


def apply(settled: Settled, stored: RecheckStored, acceptances: Acceptances, reports: Json, cfg: Config) -> Settled:
    """По предмету: принят — accepted; провал — переоткрыт с его отчётами, round 0; функция без
    провала статики — checking в режиме recheck (прогоны позже); unknown — ожидание пользователя;
    записи recheck."""
    s, notes = stored.state, list(settled.notes)
    els = dict(s["elements"])
    for subject, accepted in zip(stored.subjects, acceptances):
        e, failed = els[subject], any(f["subject"] == subject for f in stored.failures)
        if accepted.accepted:
            els[subject] = {**e, "state": "accepted"}
        elif failed:
            mine = [r for r in reports if r["subject"] == subject]
            els[subject] = {**e, "state": "repairing", "reports": mine, "policy_path": "reopen:root", "round": 0}
        else:
            path = "recheck:" if subject.startswith("function:") else f"user:unknown:{e.get('policy_path', '')}"
            els[subject] = {**e, "state": "checking", "policy_path": path}
        notes.append(JournalEntry(kind="recheck", subject=subject, data={"accepted": accepted.accepted}))
    return Settled(state={**s, "elements": els}, changed=list(settled.changed), notes=notes)
