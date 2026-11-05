"""Лист rptg.check.contract.logic.facts — план П4 и П5: развёртка схем в шаги (LOGIC §5 П4, I13).

Функции приняты по карточке design/rptg.check.contract.logic.yaml; обвязку пишет скрипт. Ответ сюда
приходит прошедшим П1, состояние — записью типизированного State. Шаг — условие вызываемой
операции с подстановкой (параметр → выражение CL); подставляет текст отдельный лист render. Выход
узла схемы — переменная окружения: вызов и свёртка — типа результата, отображение — списка,
запись — типа записи; накопители свёртки — n__accI. Списки ограничены K = k_lists (как в Z3).
Равенство двух значений здесь — шаг eq; как оно пишется по типу, решает лист equal.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rptg._types import TypeEnv
from rptg.check.contract.logic._types import FactPlan, OpPlan, Step

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Evidences, Json


def plan(state: Json, answer: Answer, form: Evidences, cfg: Config) -> FactPlan:
    """Для каждой операции S узла: факты — requires(S); узлы схемы по порядку: вызов —
    обязательство requires(C)[параметры ↦ источники] и факт ensures(C)[…, result ↦ выход];
    отображение и свёртка — то же для i < k_lists под условием len(список) > i, выход свёртки — шаг
    eq с накопителем под условием len(список) == i; запись — шаг eq на поле-путь, факт на
    поле-литерал; индекс [k] в источнике — обязательство len > k; цели П5 — ensures(S)[result ↦
    источник результата]. У карты схем нет — план пуст. Составной литерал фактом не выражается: в
    поле записи его путь идёт в partial, в аргументе — в unknown. Выполнимость условий (I14) — лист
    feasible."""
    if answer.kind not in ("design", "map") or not form or form[0].verdict != "pass":
        return FactPlan(applicable=False, subject=answer.subject, p5=False, ops=[], unknown=[], partial=[])
    if answer.kind == "map":
        return FactPlan(applicable=True, subject=answer.subject, p5=False, ops=[], unknown=[], partial=[])
    value, k = answer.value, cfg.limits.k_lists
    decimal = "^-?[0-9]+(\\.[0-9]+)?$"
    parts = answer.node.split(".")
    owners = {".".join(parts[:i]) for i in range(1, len(parts))}
    types = {"Decimal": {"type": "string", "pattern": decimal}, "Json": {}}
    types |= {n: t["schema"] for n, t in state["types"].items() if t["owner"] in owners}
    types |= {t["name"]: t["schema"] for t in value["types"]}
    uses = [state["cards"][u] for u in state["cards"][answer.node]["uses"]]
    pool = {c["id"].rsplit(".", 1)[-1]: c for c in uses + value["children"]}
    unknown: list = []
    partial: list = []

    def named(t):
        if t in ("string", "integer", "number", "boolean"):
            return {"type": t}
        return {"type": "array", "items": named(t[1:-1])} if t[:1] + t[-1:] == "[]" else types.get(t, {})

    def resolve(s):
        for _ in range(8):  # кольцо псевдонимов не зациклит
            if not (isinstance(s, dict) and "$ref" in s):
                break
            s = named(s["$ref"])
        return s if isinstance(s, dict) else {}

    def literal(v, s):
        """Литерал {const} — запись CL по типу места; составной — None."""
        if isinstance(v, str):
            return v if resolve(s).get("pattern") == decimal else '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
        if isinstance(v, bool) or v is None:
            return {True: "true", False: "false", None: "null"}[v]
        return repr(v) if isinstance(v, (int, float)) else None

    def fact(text, guard=""):
        return Step(kind="fact", text=text, subst={}, guard=guard, details={})

    def eq(left, right, s, guard=""):
        return Step(kind="eq", text=f"{left} == {right}", subst={}, guard=guard, details={"left": left, "right": right, "schema": s})

    def assign(left, src, s):
        """Поле записи равно источнику: путь — шаг eq, литерал — факт, составной литерал — в partial."""
        if isinstance(src, str):
            return [eq(left, src, s)]
        text = literal(src["const"], s)
        if text is None:
            partial.append(left)
        return [fact(f"{left} == {text}")] if text is not None else []

    def frag(v):
        return "{" + ", ".join(f"{a}: {frag(b)}" for a, b in v.items()) + "}" if isinstance(v, dict) else str(v)

    def sources(n):
        return [s for s in list(n.get("args", n.get("fields", {})).values()) + [n.get("over"), n.get("init")] if isinstance(s, str)]

    def indexes(n, base, where):
        return [Step(kind="goal", text=f"len({s[:m.start()]}) > {m.group(1)}", subst={}, guard="",
                     details={**base, "where": f"{where}: индекс {s}", "expected": f"len({s[:m.start()]}) > {m.group(1)}"})
                for s in sources(n) for m in re.finditer(r"\[(\d+)\]", s)]

    def ordered(nodes):
        ids, done, out = {n["id"] for n in nodes}, set(), []
        while len(out) < len(nodes):
            ready = [n for n in nodes if n["id"] not in done and {re.split(r"[.\[]", s)[0] for s in sources(n)} & ids <= done]
            if not ready:
                unknown.append("схема с циклом — порядок узлов не определить")
                return out
            out.append(ready[0])
            done.add(ready[0]["id"])
        return out

    def sigma(n, params, i=None):
        """Подстановка параметров вызываемого; на шаге i элемент — over[i], его поля — тоже (С-15)."""
        item, out = n.get("item"), {}
        for pn, src in n.get("args", {}).items():
            local = i is not None and isinstance(src, str) and re.split(r"[.\[]", src)[0] == item
            out[pn] = literal(src["const"], named(params.get(pn, "Json"))) if isinstance(src, dict) else \
                f"{n['over']}[{i}]{src[len(item):]}" if local else src
        if i is not None and item in params and item not in n.get("args", {}):
            out[item] = f"{n['over']}[{i}]"
        return None if None in out.values() else out

    def called(c, s, guard, details, result):
        goals = [Step(kind="goal", text=r, subst=s, guard=guard, details={**details, "expected": r}) for r in c["requires"]]
        return goals + [Step(kind="fact", text=e, subst={**s, "result": result}, guard=guard, details={}) for e in c["ensures"]]

    def mapping(n, c, params, base, where):
        steps, bound = [fact(f"len({n['id']}) == len({n['over']})")], n["item"] in params
        for i in range(k):
            s = sigma(n, params, i)
            if s is None:
                unknown.append(f"{where}: составной литерал — обязательство не выразить")
                return steps
            what = f"отображение {n['map']} по {n['over']}, шаг {i}" + (f", параметр {n['item']}" if bound else "")
            steps += called(c, s, f"len({n['over']}) > {i}", {**base, "step": i, **({"param": n["item"]} if bound else {}),
                                                              "where": f"{where}: {what}"}, f"{n['id']}[{i}]")
        return steps

    def folding(n, c, params, base, where, env_vars):
        start = literal(n["init"]["const"], named(params.get(n["acc"], "Json"))) if isinstance(n["init"], dict) else n["init"]
        accs, steps = [start] + [f"{n['id']}__acc{i}" for i in range(1, k + 1)], []
        for i in range(k):
            s = sigma(n, params, i)
            if s is None or start is None:
                unknown.append(f"{where}: составной литерал — обязательство не выразить")
                return steps
            env_vars[accs[i + 1]] = c["result"]
            what = f"свёртка {n['fold']} по {n['over']}, шаг {i}, параметр {n['item']}"
            steps += called(c, {**s, n["acc"]: accs[i]}, f"len({n['over']}) > {i}",
                            {**base, "step": i, "param": n["item"], "where": f"{where}: {what}"}, accs[i + 1])
        return steps + [eq(n["id"], accs[i], named(c["result"]), f"len({n['over']}) == {i}") for i in range(k + 1)]

    def of_node(op, n, env_vars):
        where = f"схема {op['name']}, узел {n['id']}"
        base = {"rule": "I13", "op": op["name"], "node": n["id"], "fragment": frag(n)}
        steps = indexes(n, base, where)
        if "record" in n:
            env_vars[n["id"]] = n["record"]
            props = resolve({"$ref": n["record"]}).get("properties", {})
            return steps + [x for f, src in n.get("fields", {}).items() for x in assign(f"{n['id']}.{f}", src, props.get(f, {}))]
        ref = n.get("call", n.get("map", n.get("fold", "")))
        short, _, name = ref.partition(":")
        c = next((o for o in pool.get(short, {"ops": []})["ops"] if o["name"] == name or not name), None)
        if c is None:
            unknown.append(f"{where}: операция {ref} не найдена")
            return steps
        params = {p["name"]: p["type"] for p in c["params"]}
        env_vars[n["id"]] = f"[{c['result']}]" if "map" in n else c["result"]
        if "map" in n:
            return steps + mapping(n, c, params, base, where)
        if "fold" in n:
            return steps + folding(n, c, params, base, where, env_vars)
        s = sigma(n, params)
        if s is None:
            unknown.append(f"{where}: составной литерал — обязательство не выразить")
            return steps
        return steps + called(c, s, "", {**base, "where": f"{where}: вызов {ref}"}, n["id"])

    def of_op(op):
        flow = value["flows"][op["name"]]
        env_vars = {p["name"]: p["type"] for p in op["params"]}
        steps = [fact(r) for r in op["requires"]]
        for n in ordered(flow["nodes"]):
            steps += of_node(op, n, env_vars)
        res = flow["result"]
        target = literal(res["const"], named(op["result"])) if isinstance(res, dict) else res
        steps += [Step(kind="refine", text=e, subst={"result": target}, guard="", details={"op": op["name"], "expected": e})
                  for e in op["ensures"] if target is not None]
        return OpPlan(op=op["name"], env=TypeEnv(types=types, vars=env_vars), steps=steps, keep=[p["name"] for p in op["params"]])

    ops = [of_op(op) for op in state["cards"][answer.node]["ops"] if op["name"] in value["flows"]]
    return FactPlan(applicable=True, subject=answer.subject, p5=True, ops=ops, unknown=unknown, partial=sorted(set(partial)))
