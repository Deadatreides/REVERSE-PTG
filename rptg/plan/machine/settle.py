"""Лист rptg.plan.machine.settle — следствия шага: дети принятого разложения, ревизия, подозрение на
карточку, повышение листа (LOGIC §6.1, §7.4, §7.5, §7.8) и вина в Э6 (§5).

Функции приняты по карточке design/rptg.plan.machine.yaml; обвязку пишет скрипт. Состояние — JSON.
Владелец карточки узла — разложение его родителя; владелец карточки корня — пользователь. Вина в Э6
и подозрение — две работы, две операции (после Э1 01.10.2026: в одной функции решений было 31 при
допуске 24,5). Ревизия — своя операция (после контрольных случаев 01.10.2026): она идёт по ответу,
прошедшему проверки, а не по приёмке — разложение корня принимается на утверждении, когда прежней
версии в состоянии уже нет.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import JournalEntry
from rptg.plan._types import Settled

if TYPE_CHECKING:
    from rptg._types import Config, Json
    from rptg.plan._types import Absorbed, KindDecisions


def children(absorbed: Absorbed, kinds: KindDecisions, cfg: Config) -> Settled:
    """Карта принята — разложение корня planned, если его нет. Разложение X принято (route) — дети по
    видам (финальный с кодом — stale), сборка X, записи route."""
    s, f, x = dict(absorbed.state), absorbed.facts, absorbed.route
    els, notes = dict(s["elements"]), list(absorbed.notes)
    root = next((c for c in s["cards"] if "." not in c), "")

    def blank(subject, state="planned"):
        return {"subject": subject, "kind": subject.partition(":")[0], "state": state, "attempts": 0, "form_retries": 0,
                "reports": [], "answer_hashes": []}

    def route():
        for k in kinds:
            keys = [f"design:{k.node}"] if k.kind == "composite" else [f"function:{k.node}:{o['name']}" for o in s["cards"][k.node]["ops"]]
            els.update({key: blank(key, "stale" if key.split(":", 1)[1] in s["code"] else "planned") for key in keys if key not in els})
            notes.append(JournalEntry(kind="route", subject=k.node, data={"kind": k.kind, "rule": k.rule}))
        els.setdefault(f"assembly:{x}", blank(f"assembly:{x}"))

    if f.subject == f"map:{root}" and els.get(f.subject, {}).get("state") == "accepted" and f"design:{root}" not in els:
        els[f"design:{root}"] = blank(f"design:{root}")
        notes.append(JournalEntry(kind="route", subject=f"design:{root}"))
    if x:
        route()
    s["elements"] = els
    return Settled(state=s, changed=[], notes=notes)


def revision(before: Json, settled: Settled, absorbed: Absorbed) -> Settled:
    """Ответ модели на разложение узла Y прошёл (stop accepted, у разложения на утверждении — тоже):
    версия — хэш разложения: та же, что последняя, — как есть; совпала с позапрошлой — колебание,
    ожидание пользователя; дописывается. Была прежняя версия — ревизия: карточки детей, что
    изменились, — в changed, снятые дети — их поддерево из состояния; подозреваемые под Y, чья
    карточка не менялась, продолжают: round + 1, resume к ветви default подозрения, на исчерпанной
    лестнице — extra. Прочие события — как есть."""
    f = absorbed.facts
    if f.event != "model_answered" or f.subject != f"design:{f.node}" or absorbed.step.stop != "accepted":
        return settled
    s, y = dict(settled.state), f.node
    notes = list(settled.notes)
    old = before["designs"].get(y)
    olds, news = {c["id"]: c for c in (old or s["designs"][y])["children"]}, {c["id"]: c for c in s["designs"][y]["children"]}
    moved = sorted(c for c in olds.keys() | news.keys() if olds.get(c) != news.get(c))

    def under(node, gone):
        return any(node == g or node.startswith(g + ".") for g in gone)

    def elements():
        out = {}
        for k, e in s["elements"].items():
            node = k.split(":")[1]
            if under(node, olds.keys() - news.keys()):
                continue
            same_card = old and node.rpartition(".")[0] == y and node not in moved
            out[k] = resume(e) if same_card and e["state"] == "card_suspect" else e
        return out

    def resume(e):
        steps = (e.get("policy_path") or "").split("/")
        to = "resume:" + "/".join(steps[:-1]) + "/default" if steps[-1].startswith("case[") else "extra:root"
        return {**e, "state": "planned", "round": e.get("round", 0) + 1, "policy_path": to}

    def version(el):
        versions = el.get("versions") or []
        if absorbed.design_hash in versions[-1:]:
            return el
        if versions[-2:-1] == [absorbed.design_hash]:
            notes.append(JournalEntry(kind="oscillation", subject=f"design:{y}", data={"versions": versions[-2:]}))
            el = {**el, "policy_path": f"user:oscillation:{el.get('policy_path', '')}"}
        return {**el, "versions": versions + [absorbed.design_hash]}

    els = elements()
    els[f"design:{y}"] = version(els[f"design:{y}"])
    s["elements"] = els
    return Settled(state=s, changed=sorted(set(settled.changed) | set(moved)), notes=notes)


def suspect(settled: Settled, absorbed: Absorbed, cfg: Config) -> Settled:
    """stop exhausted у функции ниже max_depth — повышение: функции узла promoted, design:узел
    planned, запись promotion. stop card_suspect или exhausted (разложение, max_depth), Э3 с малом
    годных входов — подозрение на карточку узла: корень — ожидание пользователя; round ≥ 1 — повтор
    состояния, ожидание пользователя; иначе владелец — разложение родителя — переоткрывается с
    отчётами элемента."""
    s, f, st = dict(settled.state), absorbed.facts, absorbed.step
    els, notes = dict(s["elements"]), list(settled.notes)
    subject, node = f.subject, f.node
    el = els.get(subject) or {}
    few = any(e.check == "E3" and isinstance(e.details, dict) and e.details.get("reason") == "мало годных входов" for e in f.unknown)
    stop = st.stop if st.wait == "stop" else ""

    def promote():
        for k in [k for k in els if k.startswith(f"function:{node}:")]:
            els[k] = {**els[k], "state": "promoted"}
        els.setdefault(f"design:{node}", {"subject": f"design:{node}", "kind": "design", "state": "planned", "attempts": 0,
                                          "form_retries": 0, "reports": [], "answer_hashes": []})
        notes.append(JournalEntry(kind="promotion", subject=f"design:{node}"))

    def suspicion():
        extra = [{"subject": subject, "layer": "E3", "rule": "E3", "where": subject, "means": "мало годных входов",
                  "expected": "требования, из которых Hypothesis находит годные входы: уточнить границы в requires"}] if few else []
        parent = node.rpartition(".")[0]
        if not parent or el.get("round", 0) >= 1:
            reason = "repeat" if parent else "exhausted"
            els[subject] = {**el, "state": "card_suspect", "policy_path": f"user:{reason}:{st.path}"}
            notes.append(JournalEntry(kind="stop", subject=subject, data={"reason": reason}))
            return
        owner = f"design:{parent}"
        els[owner] = {**els[owner], "state": "repairing", "reports": el.get("reports", []) + extra, "policy_path": "reopen:root"}
        notes.append(JournalEntry(kind="suspect", subject=subject, data={"owner": owner}))

    if stop == "exhausted" and subject.startswith("function:") and f.level < cfg.limits.max_depth:
        promote()
    elif stop in ("exhausted", "card_suspect") or few:
        suspicion()
    s["elements"] = els
    return Settled(state=s, changed=settled.changed, notes=notes)


def blame(settled: Settled, absorbed: Absorbed, cfg: Config) -> Settled:
    """stop blame у сборки: виновный — из подробностей первого провала Э6, по умолчанию разложение
    узла; design:X или function:узел:операция переоткрывается с отчётами сборки (запись blame);
    card:X — карточка X под подозрением: переоткрывается её владелец — разложение родителя X, у
    корня — разложение корня; иначе — как есть."""
    f, st = absorbed.facts, absorbed.step
    if st.wait != "stop" or st.stop != "blame":
        return settled
    s, notes = dict(settled.state), list(settled.notes)
    els = dict(s["elements"])
    found = [e.details.get("blame") for e in f.failures if e.check == "E6" and isinstance(e.details, dict)]
    target = (found[0] if found else None) or f"design:{f.node}"
    if target.startswith("card:"):
        card = target.split(":")[1]
        target = "design:" + (card.rpartition(".")[0] or card)
    if target in els:
        els[target] = {**els[target], "state": "repairing", "reports": (els.get(f.subject) or {}).get("reports", []),
                       "policy_path": "reopen:root"}
        notes.append(JournalEntry(kind="blame", subject=target, data={"from": f.subject}))
    s["elements"] = els
    return Settled(state=s, changed=settled.changed, notes=notes)
