"""Лист rptg.plan.machine.policy — политика элемента: деревья по умолчанию (LOGIC §7.3), валидатор и
пошаговый исполнитель на языке комплексов arch2 (trace-probe/arch2: genotype.py, runner.py).

Функции приняты по карточке design/rptg.plan.machine.yaml; обвязку пишет скрипт. arch2 исполняет
генотип одним прогоном и сам зовёт модели; ядро rptg чисто, поэтому генотип исполняется от события
к событию: позиция — Element.policy_path, путь в записи arch2 (root/seq[i]/case[v]/default/par[i]/
budget) с приставкой режима (reopen, resume, extra, recheck, user). Детерминизм, STOP завершает всё,
у PAR побеждает первая ветвь с приёмкой — как в runner arch2 (SPEC §7.2).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import PolicyNode
from rptg.plan._types import Policies, PolicyStep

if TYPE_CHECKING:
    from rptg._types import Assignments, Config, Json, Override
    from rptg.plan._types import Obs


def build(cfg: Config) -> Policies:
    """У роли своя политика cfg.policies[роль] — её корень, иначе дерево по умолчанию: SEQ ступеней
    по длине лестницы роли и STOP(exhausted). Ступень 1: CALL assigned, CHECK, SWITCH подтипа. Ступень
    k > 1: CALL next с отчётом, CHECK, форма, тот же провал — подозрение, подтип. Повторы формы и
    починки — repair.form_retries и repair.per_rung штук. Дерево extra — лишний круг."""
    forms_n, repairs_n = cfg.repair.form_retries, cfg.repair.per_rung

    def n(op, **kw): return PolicyNode(op=op, **kw)  # noqa: E704
    def seq(*kids): return n("SEQ", children=list(kids))  # noqa: E704
    def call(who, wording, report): return n("CALL", operator=who, wording=wording, with_report=report)  # noqa: E704
    def sw(obs, cases, default=None): return n("SWITCH", obs=obs, cases=cases, default=default or n("CHECK"))  # noqa: E704
    def done(reason): return n("STOP", reason=reason)  # noqa: E704

    def forms(k):
        return n("CHECK") if k == 0 else seq(call("same", "alternative", False), n("CHECK"),
                                             sw("violation_subtype", {"none": done("accepted"), "form": forms(k - 1)}))

    def repairs(k):
        more = {"contract": repairs(k - 1), "semantic": repairs(k - 1)} if k else {}
        return n("CHECK") if k == 0 else seq(call("same", "primary", True), n("CHECK"),
                                             sw("violation_subtype", {"none": done("accepted"), "form": forms(forms_n), **more}))

    def rung(k):
        cheap = {"contract": repairs(repairs_n), "semantic": repairs(repairs_n)}
        if k == 1:
            return seq(call("assigned", "primary", False), n("CHECK"),
                       sw("violation_subtype", {"none": done("accepted"), "form": forms(forms_n), **cheap}))
        return seq(call("next", "primary", True), n("CHECK"), sw("violation_subtype", {"form": forms(forms_n)}),
                   sw("same_failure", {"SAME": done("card_suspect")}), sw("violation_subtype", {"none": done("accepted"), **cheap}))

    def tree(role):
        own = (cfg.policies or {}).get(role)
        return own.root if own else seq(*[rung(k) for k in range(1, len(getattr(cfg.roles, role)) + 1)], done("exhausted"))

    extra = seq(call("same", "primary", True), n("CHECK"), sw("violation_subtype", {"none": done("accepted")}, done("user")))
    return Policies(architect=tree("architect"), designer=tree("designer"), implementer=tree("implementer"), extra=extra, problems=[])


def check(policies: Policies, cfg: Config) -> Policies:
    """У каждого дерева обходом сверху вниз, путь в записи arch2; проблема — «роль: путь: что»: CALL —
    оператор не assigned, same, next и не оператор проекта, формулировка, за CALL в его SEQ нет CHECK;
    SEQ и PAR — пустые дети, у SEQ узлы после STOP; SWITCH — неизвестная наблюдаемая, значение не из
    неё, нет default, tokens_bucket вне BUDGET; BUDGET — лимит не положителен или нет child; STOP без
    причины; неизвестный узел."""
    values = {"violation_subtype": {"none", "form", "contract", "dependency", "semantic", "value", "other"},
              "same_failure": {"SAME", "DIFFERENT", "NA"}, "attempts_used": {"0", "1", "2", "3+"},
              "work_class": {"map", "design", "io", "compute", "search", "text", "transform"},
              "tokens_bucket": {"0", "low", "mid", "high"}}
    operators, problems = {"assigned", "same", "next"} | set(cfg.operators), []

    def bad(role, path, what):
        problems.append(f"{role}: {path}: {what}")

    def on_call(role, n, path, checked, budget):
        if n.operator not in operators:
            bad(role, path, f"оператор {n.operator} не assigned, same, next и не оператор проекта")
        if n.wording not in ("primary", "alternative"):
            bad(role, path, f"формулировка {n.wording}")
        if not checked:
            bad(role, path, "за CALL нет CHECK")

    def on_list(role, n, path, checked, budget):
        kids = n.children or []
        if not kids:
            bad(role, path, "пустой список детей")
        if n.op == "SEQ" and any(c.op == "STOP" for c in kids[:-1]):
            bad(role, path, "после STOP в SEQ есть узлы")
        for i, c in enumerate(kids):
            walk(role, c, f"{path}/{n.op.lower()}[{i}]", n.op == "SEQ" and kids[i + 1:i + 2] != [] and kids[i + 1].op == "CHECK", budget)

    def on_switch(role, n, path, checked, budget):
        allowed = values.get(n.obs)
        if allowed is None or n.obs == "tokens_bucket" and not budget:
            bad(role, path, f"неизвестная наблюдаемая {n.obs}" if allowed is None else "tokens_bucket вне BUDGET")
        for v, c in sorted((n.cases or {}).items()):
            if allowed is not None and v not in allowed:
                bad(role, path, f"значение {v} не из наблюдаемой {n.obs}")
            walk(role, c, f"{path}/case[{v}]", False, budget)
        if n.default is None:
            bad(role, path, "нет default")
        else:
            walk(role, n.default, f"{path}/default", False, budget)

    def on_budget(role, n, path, checked, budget):
        if not n.limit_tokens or n.limit_tokens <= 0:
            bad(role, path, "лимит BUDGET не положителен")
        if n.child is None:
            bad(role, path, "нет child")
        else:
            walk(role, n.child, f"{path}/budget", False, True)

    def on_stop(role, n, path, checked, budget):
        if not n.reason:
            bad(role, path, "STOP без причины")

    def on_other(role, n, path, checked, budget):
        if n.op != "CHECK":
            bad(role, path, f"неизвестный узел {n.op}")

    def walk(role, n, path, checked, budget):
        handlers = {"CALL": on_call, "SEQ": on_list, "PAR": on_list, "SWITCH": on_switch, "BUDGET": on_budget, "STOP": on_stop}
        handlers.get(n.op, on_other)(role, n, path, checked, budget)

    for role in ("architect", "designer", "implementer", "extra"):
        walk(role, getattr(policies, role), "root", False, False)
    return Policies(architect=policies.architect, designer=policies.designer, implementer=policies.implementer,
                    extra=policies.extra, problems=list(policies.problems) + problems)


def step(policies: Policies, state: Json, subject: str, obs: Obs, idle: Obs, manual: Override, event: str,
         assignments: Assignments, cfg: Config) -> PolicyStep:
    """Ответ пользователя и команда — none; сборка и перепроверка — без дерева; элемент ждёт
    пользователя — none. Вызов в позиции: хранимый путь на CALL — он, иначе исполнение от начала
    режима по наблюдаемым idle до первого CALL. dispatch — этот вызов; ответ модели — повтор оставляет
    его, unknown — stop unknown, иначе исполнение от следующего за ним узла; прогон — от хранимой
    позиции (CHECK) по наблюдаемым события. Рамка BUDGET — расход наблюдаемых: позиция ищется по
    расходу до события, дальше — после; вход в исчерпанную рамку и приход к CALL под ней — stop
    budget (рамка ограничивает следующие вызовы, а не полученный ответ). Приход к CALL: assigned —
    назначение элемента, same — текущий оператор, next — ступень + 1 не выше min(лестница, max_rung),
    иначе stop exhausted; имя оператора — он."""
    el, kind = state["elements"].get(subject) or {}, subject.partition(":")[0]
    stored = el.get("policy_path") or ""
    head, _, tail = stored.partition(":")
    mode, path = (head, tail) if head in ("user", "extra", "reopen", "resume", "recheck") else ("", stored)

    def made(wait, at="", stop="", operator="", rung=0, wording="primary", report=False):
        return PolicyStep(wait=wait, path=at, stop=stop, operator=operator, rung=rung, wording=wording, report=report)

    def verify():
        where = "recheck:" if mode == "recheck" else ""
        if not obs.complete:
            return made("check", where)
        if obs.unknown:
            return made("stop", where, "unknown")
        return made("stop", where, "accepted" if obs.accepted else "blame" if kind == "assembly" else "reopen")

    if event in ("user_answered", "command") or not kind or mode == "user":
        return made("none")
    if kind == "assembly" or mode == "recheck":
        return verify()
    a = el.get("assignment") or {"role": assignments[0].role, "rung": assignments[0].rung, "operator": assignments[0].operator}
    ladder = getattr(cfg.roles, a["role"])
    cap = min(len(ladder), manual.max_rung or len(ladder))
    tree, prefix = (policies.extra, "extra:") if mode == "extra" else (getattr(policies, a["role"]), "")

    def at(steps):
        n = tree
        for s in steps[1:]:
            name, _, idx = s.rstrip("]").partition("[")
            n = {"seq": lambda: n.children[int(idx)], "par": lambda: n.children[int(idx)], "case": lambda: n.cases[idx],
                 "default": lambda: n.default, "budget": lambda: n.child}[name]()
        return n

    def after(steps, o):
        while len(steps) > 1:
            *up, last = steps
            name, _, idx = last.rstrip("]").partition("[")
            if name in ("seq", "par") and int(idx) + 1 < len(at(up).children) and (name == "seq" or not o.accepted):
                return up + [f"{name}[{int(idx) + 1}]"]
            steps = up
        return None

    def case(n, steps, o):
        if n.obs == "tokens_bucket":
            limit = next(at(steps[:i]).limit_tokens for i in range(len(steps), 0, -1) if at(steps[:i]).op == "BUDGET")
            t = o.tokens
            v = "0" if t == 0 else "low" if 3 * t < limit else "mid" if 3 * t < 2 * limit else "high"
        else:
            v = {"violation_subtype": o.subtype, "same_failure": o.same, "work_class": o.work,
                 "attempts_used": str(min(o.attempts, 3)).replace("3", "3+")}[n.obs]
        return f"case[{v}]" if v in (n.cases or {}) else "default"

    def arrive(n, where, rung, operator, first):
        if n.operator == "next" and rung >= cap:
            return made("stop", where, "exhausted", rung=rung)
        if n.operator == "next":
            rung, operator = rung + 1, ladder[rung]
        elif n.operator not in ("assigned", "same"):
            rung, operator = (ladder.index(n.operator) + 1 if n.operator in ladder else rung), n.operator
        return made("call", where, "", operator, rung, n.wording, bool(n.with_report) or mode == "reopen" and first)

    def spent(steps, o):
        return any(at(steps[:i]).op == "BUDGET" and o.tokens >= at(steps[:i]).limit_tokens for i in range(1, len(steps) + 1))

    def run(steps, o, rung, operator, first):
        while steps is not None:
            n, where = at(steps), prefix + "/".join(steps)
            if n.op in ("CALL", "BUDGET") and spent(steps, o):
                return made("stop", where, "budget", rung=rung)
            if n.op in ("CALL", "STOP"):
                return arrive(n, where, rung, operator, first) if n.op == "CALL" else made("stop", where, n.reason, rung=rung)
            if n.op == "CHECK" and not o.complete:
                return made("check", where, rung=rung, operator=operator)
            steps = {"SEQ": lambda: steps + ["seq[0]"], "PAR": lambda: steps + ["par[0]"], "BUDGET": lambda: steps + ["budget"],
                     "CHECK": lambda: after(steps, o), "SWITCH": lambda: steps + [case(n, steps, o)]}[n.op]()
        return made("stop", "", "accepted" if o.accepted else "exhausted", rung=rung)

    def locate():
        split = path.split("/") if path else ["root"]
        here = at(split)
        if path and here.op == "CALL":
            return made("call", prefix + path, "", a["operator"], a["rung"], here.wording, bool(here.with_report) or mode == "reopen")
        return run(split, idle, a["rung"], a["operator"], True)

    def answer():
        cur = locate()
        if event == "sandbox_finished":
            return run(path.split("/") if path else ["root"], obs, a["rung"], a["operator"], False)
        if event == "dispatch" or cur.wait != "call":
            return cur
        if obs.repeat:
            return made("call", ("reopen:" if mode == "reopen" else "") + cur.path, "", cur.operator, cur.rung, cur.wording, cur.report)
        if obs.unknown:
            return made("stop", cur.path, "unknown", rung=cur.rung)
        return run(after(cur.path[len(prefix):].split("/"), obs), obs, cur.rung, cur.operator, False)

    return answer()
