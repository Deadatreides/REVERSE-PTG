"""Лист rptg.plan.machine.intake — что принесло событие, запись доказательств, расхода и чистого
ответа, наблюдаемые элемента (LOGIC §7.2, §7.3).

Функции приняты по карточке design/rptg.plan.machine.yaml; обвязку пишет скрипт. Состояние — JSON:
листья читают и строят словари с именами полей JSON (class, а не class_). Десятичные — записи:
модуль decimal узлу не разрешён, сложение точное — в целых с общим масштабом.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import RawAnswer
from rptg.plan._types import EventFacts, Obs, ReadyItem

if TYPE_CHECKING:
    from rptg._types import Acceptance, Answer, Assignments, Config, Decimal, Event, Evidences, Json, Sha
    from rptg.plan.machine._types import Reports


def facts(state: Json, event: Event, evidence: Evidences, answer: Answer, cfg: Config) -> EventFacts:
    """Предмет: у ответа модели — предмет задачи; у прогона — function:узел:операция или
    assembly:узел по цели; у ответа пользователя — design:X утверждения, предмет решения или
    перепроверки; у команды — карта корня. Роль — из задачи, иначе из назначения элемента, иначе по
    виду. Элемент — текущий или новый planned. Разложение узла — чистый ответ разложения, иначе
    текущее. ready — элемент ответа модели без назначения."""
    kind, task = event.kind, event.task
    root = next((c for c in state["cards"] if "." not in c), None) or next(iter(state["user_examples"]), ":").split(":")[0]
    reply = event.reply if isinstance(event.reply, dict) else {}

    def subject_of():
        if kind == "model_answered":
            return task.subject
        if kind == "sandbox_finished":
            return ("function:" if event.target.kind == "function_tests" else "assembly:") + event.target.subject
        if kind == "user_answered" and "approve" in reply:
            return f"design:{reply['approve']}"
        asked = reply.get("decide") or reply.get("recheck") if kind == "user_answered" else None
        return asked or f"map:{root}"

    subject = subject_of()
    sort, _, rest = subject.partition(":")
    node, _, op = rest.partition(":")
    element = state["elements"].get(subject) or {"subject": subject, "kind": sort, "state": "planned", "attempts": 0,
                                                  "form_retries": 0, "reports": [], "answer_hashes": []}

    def role_of():
        if task:
            return task.role
        if element.get("assignment"):
            return element["assignment"]["role"]
        return "architect" if node == root and sort in ("map", "design") else {"function": "implementer"}.get(sort, "designer")

    def design_of(failures, unknown):
        clean = answer.ok and answer.kind == "design" and not failures and not unknown
        return {**answer.value, "node": node} if clean else state["designs"].get(node, {})

    def ready_of(role):
        fresh = kind == "model_answered" and not element.get("assignment")
        return [ReadyItem(subject=subject, kind=sort, role=role, level=node.count(".") + 1, node=node, op=op or None)] if fresh else []

    def verdicts(verdict):
        return [e for e in evidence if e.verdict == verdict]

    role, failures, unknown = role_of(), verdicts("fail"), verdicts("unknown")
    raw = event.answer or RawAnswer(text="", input_tokens=0, output_tokens=0, cache_read_tokens=0, finish_reason="", refusal=False)
    operator = (cfg.operators.get(task.operator) if task else None) or next(iter(cfg.operators.values()))
    return EventFacts(event=kind, subject=subject, node=node, level=node.count(".") + 1, role=role,
                      attempt=task.attempt if task else 0, element=element, failures=failures, unknown=unknown, text=raw.text,
                      raw=raw, operator=operator, reply=reply, design=design_of(failures, unknown), ready=ready_of(role))


def store(state: Json, facts: EventFacts, answer: Answer, evidence: Json, hash: Sha, cost: Decimal, assignments: Assignments,
          cfg: Config) -> Json:
    """Доказательства события дописываются к предмету; у ответа модели: не повтор по хэшу —
    attempts = max(attempts, попытка задачи) и хэш в answer_hashes; tokens и cost элемента и spent
    бюджета растут на расход; элементу без назначения — восстановленное; чистый ответ (извлечён, без
    провалов и unknown) пишется: карта — текст, карточка корня, типы; разложение — само, карточки
    детей, его типы; функция — код."""
    subject, el = facts.subject, dict(facts.element)
    if facts.event not in ("model_answered", "sandbox_finished"):
        return state
    state = dict(state)

    def add(a, b):
        def num(text):
            whole, _, frac = text.lstrip("-").partition(".")
            return (-1 if text.startswith("-") else 1) * int(whole + (frac + "0" * 18)[:18])
        total = num(a) + num(b)
        whole, frac = divmod(abs(total), 10 ** 18)
        return ("-" if total < 0 else "") + str(whole) + ("." + f"{frac:018d}".rstrip("0") if frac else "")

    def restore(a):
        op, ladder = facts.operator.id, getattr(cfg.roles, a.role)
        return {"subject": subject, "role": a.role, "class": a.class_, "operator": op,
                "rung": ladder.index(op) + 1 if op in ladder else a.rung, "decided_by": a.decided_by if a.operator == op else "table"}

    def write(value):
        if answer.kind == "map":
            state["map_text"], state["cards"] = value["map_text"], {**state["cards"], value["card"]["id"]: value["card"]}
            state["types"] = {**state["types"], **{t["name"]: t for t in value["types"]}}
        elif answer.kind == "design":
            state["designs"] = {**state["designs"], answer.node: {**value, "node": answer.node}}
            state["cards"] = {**state["cards"], **{c["id"]: c for c in value["children"]}}
            state["types"] = {**state["types"], **{t["name"]: t for t in value.get("types") or []}}
        elif answer.kind == "function":
            state["code"] = {**state["code"], f"{answer.node}:{answer.op}": answer.code}

    state["evidence"] = {**state["evidence"], subject: state["evidence"].get(subject, []) + list(evidence)}
    if facts.event == "model_answered":
        if hash not in el["answer_hashes"]:
            el["attempts"], el["answer_hashes"] = max(el["attempts"], facts.attempt), el["answer_hashes"] + [hash]
        el["tokens"] = el.get("tokens", 0) + facts.raw.input_tokens + facts.raw.output_tokens
        el["cost"] = add(el["cost"], cost) if el.get("cost") is not None else cost
        state["budget"] = {**state["budget"], "spent": add(state["budget"]["spent"], cost)}
        if not el.get("assignment") and assignments:
            el["assignment"] = restore(assignments[0])
        if answer.ok and not facts.failures and not facts.unknown:
            write(answer.value)
    state["elements"] = {**state["elements"], subject: el}
    return state


def observe(state: Json, facts: EventFacts, reports: Reports, acceptance: Acceptance, hash: Sha) -> Obs:
    """Подтип — по первому провалу; same — подпись отчётов (слой, правило, место) против отчётов
    элемента до события; текущий хэш — у последнего доказательства предмета; complete — на нём есть
    провал или unknown, либо все слои; unknown — провалов нет, а есть unknown или всё на месте без
    приёмки; repeat — хэш ответа уже был у элемента."""
    subject, before, failures = facts.subject, facts.element, facts.failures
    el = state["elements"].get(subject, before)

    def subtype(e):
        details = e.details if isinstance(e.details, dict) else {}
        if e.check == "E1":
            return "form" if "reason" in details or "не разбирается" in " ".join(details.get("problems") or []) else "contract"
        return {"P1": "form", "P2": "contract", "P3": "contract", "P4": "dependency", "P5": "semantic", "P7": "semantic",
                "E2": "value", "E3": "value", "E6": "value"}.get(e.check, "other")

    def same():
        old = {(r["layer"], r["rule"], r["where"]) for r in before["reports"]}
        if not failures or not old:
            return "NA"
        return "SAME" if {(r.layer, r.rule, r.where) for r in reports} == old else "DIFFERENT"

    def current():
        evs = state["evidence"].get(subject, [])
        return [e for e in evs if e["subject_hash"] == evs[-1]["subject_hash"]]

    def complete(now):
        seen = {e["check"] for e in now} | {e["check"] + "/" + e["tool"] for e in now}
        need = {"function": {"E1/mypy", "E2", "E3"}, "assembly": {"E6"}}.get(subject.partition(":")[0], set())
        return bool(now) and (any(e["verdict"] != "pass" for e in now) or need <= seen)

    now = current()
    done = complete(now)
    unknown = not failures and (any(e["verdict"] == "unknown" for e in now) or done and not acceptance.accepted)
    return Obs(subtype=subtype(failures[0]) if failures else "none", same=same(), attempts=el["attempts"],
               work=(el.get("assignment") or {}).get("class") or "map", tokens=el.get("tokens", 0), complete=done,
               accepted=acceptance.accepted, unknown=unknown, repeat=facts.event == "model_answered" and hash in before["answer_hashes"])


def idle(state: Json, subject: str, assignments: Assignments) -> Obs:
    """Наблюдаемые самого элемента без нового события — чтобы найти вызов в позиции: подтип —
    последний подтип элемента, same — NA, попытки и tokens элемента, класс — назначения элемента,
    иначе первого из списка, иначе map."""
    el = state["elements"].get(subject) or {}
    work = (el.get("assignment") or {}).get("class") or (assignments[0].class_ if assignments else "map")
    return Obs(subtype=el.get("last_subtype") or "none", same="NA", attempts=el.get("attempts", 0), work=work,
               tokens=el.get("tokens", 0), complete=True, accepted=False, unknown=False, repeat=False)
