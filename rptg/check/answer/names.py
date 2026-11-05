"""Лист rptg.check.answer.names — нарушения П1, видимые без языка (LOGIC §5 П1, шаги 4–5).

Функции приняты по карточке design/rptg.check.answer.yaml; обвязку пишет скрипт. Ответ сюда
приходит только прошедшим схему метода, состояние — записью типизированного State: обязательные
поля читаются напрямую, и нарушенная согласованность роняет проверку (ERROR), а не прячется.
"""
from __future__ import annotations

import ast
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Answer, Json, Strings
    from rptg.check._types import Validations


def problems(state: Json, answer: Answer, checked: Validations) -> Strings:
    """Тип параметра, результата и ссылки в схеме нового типа видим (§2.5); короткое имя операции в
    схеме находится ровно одно — среди детей, потом среди uses узла (§2.3); параметр не result и не
    слово Python (Н-1); переменная квантора не совпадает с параметром и result — иначе подстановка
    в П4 заденет связанную переменную. Ответ не прошёл схему — пусто."""
    if not checked or not all(v.ok for v in checked):
        return []
    value = answer.value

    def context():
        visible = {"string", "integer", "number", "boolean", "Decimal", "Json"} | {t["name"] for t in value["types"]}
        if answer.kind != "design":
            return visible, [value["card"]], []
        parts = answer.node.split(".")
        owners = {".".join(parts[:i]) for i in range(1, len(parts))}
        visible |= {n for n, t in state["types"].items() if t["owner"] in owners}
        return visible, value["children"], [state["cards"][u] for u in state["cards"][answer.node]["uses"]]

    visible, cards, uses = context()

    def taken(name):
        try:
            ast.parse(f"{name} = 0")
        except SyntaxError:
            return True
        return name == "result"

    def of_op(where, op):
        names, out = {p["name"] for p in op["params"]} | {"result"}, []
        for p in op["params"]:
            if taken(p["name"]):
                out.append(f"{where}: имя параметра {p['name']} занято (result или слово Python)")
            if p["type"].strip("[]") not in visible:
                out.append(f"{where}: тип параметра {p['name']} — {p['type']} не виден")
        if op["result"].strip("[]") not in visible:
            out.append(f"{where}: тип результата {op['result']} не виден")
        for text in op["requires"] + op["ensures"]:
            out += [f"{where}: переменная квантора {v} совпадает с параметром или result в «{text}»"
                    for v in re.findall(r"\b(?:forall|exists)\s+([A-Za-z_]\w*)\s+in\b", text) if v in names]
        return out

    def resolve(ref):
        short, _, name = ref.partition(":")
        found = [c for c in cards if c["id"].endswith("." + short)] or [c for c in uses if c["id"].endswith("." + short)]
        if len(found) != 1:
            return "не найдена" if not found else "неоднозначна"
        ops = [o["name"] for o in found[0]["ops"]]
        return None if (name or (ops[0] if len(ops) == 1 else "")) in ops else "операция не найдена или не указана"

    def of_flows():
        out = []
        for fname, flow in value.get("flows", {}).items():
            for n in flow["nodes"]:
                ref = n.get("call", n.get("map", n.get("fold")))
                why = resolve(ref) if ref else None
                if why:
                    out.append(f"схема {fname}, узел {n['id']}: {ref} — {why}")
        return out

    out = [f"тип {t['name']}: ссылка на невидимый тип {r}" for t in value["types"]
           for r in re.findall(r'"\$ref": "([^"]*)"', json.dumps(t["schema"])) if r not in visible]
    out += [p for card in cards for op in card["ops"] for p in of_op(f"{card['id']}:{op['name']}", op)]
    return out + of_flows()
