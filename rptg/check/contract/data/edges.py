"""Лист rptg.check.contract.data.edges — рёбра схем разложения для П3 (LOGIC §5 П3, I12).

Функции приняты по карточке design/rptg.check.contract.data.yaml; обвязку пишет скрипт. Ответ сюда
приходит прошедшим П1, состояние — записью типизированного State. Источник, которого нет, ребра не
даёт: его покажет П2 (I5).
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rptg._types import TypeEnv
from rptg.check._types import ValidateJob
from rptg.check.contract.data._types import EdgeJob, EdgeJobs, PathJob, SubJob

if TYPE_CHECKING:
    from rptg._types import Answer, Evidences, Json


def jobs(state: Json, answer: Answer, form: Evidences, edges: Json) -> EdgeJobs:
    """По схемам операций узла: аргументы вызовов, поля записей, элемент отображения и свёртки (путь
    по [0]; поле элемента — тоже, С-15), начальное значение свёртки и результат схемы. Источник с
    путём — задание пути от типа параметра или выхода узла, без пути — имя типа; поле записи — путь
    от типа записи. Литерал — задание проверки по типу места. Рёбра из edges — прямые задания
    подтипа. Окружение — Decimal, Json, типы строгих предков узла и новые типы ответа."""
    direct = [SubJob(where=f"ребро {i}", a=e["source_type"], b=e["target_type"],
                     env=TypeEnv(types=e["env"]["types"], vars=e["env"]["vars"])) for i, e in enumerate(edges, 1)]
    if answer.kind != "design" or not form or form[0].verdict != "pass":
        return EdgeJobs(applicable=bool(direct), subject=answer.subject, edges=[], paths=[],
                        env=TypeEnv(types={}, vars={}), direct=direct, consts=[])
    value, card = answer.value, state["cards"][answer.node]

    def visible():
        parts = answer.node.split(".")
        owners = {".".join(parts[:i]) for i in range(1, len(parts))}
        found = {"Decimal": {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}, "Json": {}}
        found |= {n: t["schema"] for n, t in state["types"].items() if t["owner"] in owners}
        return found | {t["name"]: t["schema"] for t in value["types"]}

    types = visible()
    env = TypeEnv(types=types, vars={})
    pool = {c["id"].rsplit(".", 1)[-1]: c for c in [state["cards"][u] for u in card["uses"]] + value["children"]}
    found: list = []
    paths: list = []
    consts: list = []

    def callee(n):
        short, _, name = n.get("call", n.get("map", n.get("fold", ""))).partition(":")
        return next((o for o in pool.get(short, {"ops": []})["ops"] if o["name"] == name or not name), None)

    def outputs(nodes):
        out = {}
        for n in nodes:
            op = callee(n) if "record" not in n else {"result": n["record"]}
            if op:
                out[n["id"]] = f"[{op['result']}]" if "map" in n else op["result"]
        return out

    def side(src, known):
        head = re.split(r"[.\[]", src, maxsplit=1)[0]
        rest = src[len(head):].lstrip(".")
        if head not in known or not rest:
            return (known[head], -1) if head in known else None
        paths.append(PathJob(root=known[head], path=rest, env=env))
        return "", len(paths) - 1

    def edge(where, src, target, known, target_schema=None):
        if isinstance(src, dict):
            name = target[0] or "·литерал"
            types_here = types | ({name: target_schema} if target_schema is not None else {})
            consts.append(ValidateJob(where=where, value=src["const"], type=name, env=TypeEnv(types=types_here, vars={})))
            return
        a = side(src, known)
        if a:
            found.append(EdgeJob(where=where, a=a[0], a_at=a[1], b=target[0], b_at=target[1]))

    def element(src, item, over):
        """Поле элемента отображения или свёртки (С-15) — путь по [0] от списка over."""
        local = isinstance(src, str) and item is not None and re.split(r"[.\[]", src, maxsplit=1)[0] == item
        return over + "[0]" + src[len(item):] if local else src

    def field(record, name):
        s = types.get(record, {}).get("properties", {}).get(name, {})
        if set(s) == {"$ref"}:
            return (s["$ref"], -1), None
        paths.append(PathJob(root=record, path=name, env=env))
        return ("", len(paths) - 1), s

    def of_record(where, n, known):
        for f, src in n.get("fields", {}).items():
            target, schema = field(n["record"], f)
            edge(f"{where}: {src if isinstance(src, str) else 'литерал'} → {n['record']}.{f}", src, target, known, schema)

    def of_node(op, n, known):
        where = f"{op['name']}, узел {n['id']}"
        if "record" in n:
            of_record(where, n, known)
            return
        c = callee(n)
        params = {p["name"]: p["type"] for p in c["params"]} if c else {}
        item, args = n.get("item"), n.get("args", {})
        over = n["over"] if isinstance(n.get("over"), str) else ""
        for pn, src in args.items():
            edge(f"{where}: {src if isinstance(src, str) else 'литерал'} → {pn}", element(src, item, over), (params.get(pn, "Json"), -1), known)
        if item in params and item not in args:
            edge(f"{where}: элемент → {item}", over + "[0]", (params[item], -1), known)
        if "fold" in n:
            edge(f"{where}: {n['init']} → {n['acc']}", n["init"], (params.get(n["acc"], "Json"), -1), known)

    for op in card["ops"]:
        flow = value["flows"].get(op["name"])
        if flow is None:
            continue
        known = {p["name"]: p["type"] for p in op["params"]} | outputs(flow["nodes"])
        for n in flow["nodes"]:
            of_node(op, n, known)
        edge(f"{op['name']}, результат: {flow['result']} → {op['result']}", flow["result"], (op["result"], -1), known)
    return EdgeJobs(applicable=True, subject=answer.subject, edges=found, paths=paths, env=env, direct=direct, consts=consts)
