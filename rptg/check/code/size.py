"""Лист rptg.check.code.size — размер функции для Э1 (LOGIC §5, REVERSE-PTG-LIMIT-FUNCTION.md).

Функции приняты по карточке design/rptg.check.code.yaml; обвязку пишет скрипт. Перенос затравки
tools/leafcheck0.py; решения и сложность блоков считает radon, вложенные функции — отдельными
блоками. Закон «две строки на решение»: на 21 функции листьев lang строк кода = 2,01·D − 3,9.
"""
from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from radon.complexity import cc_visit

if TYPE_CHECKING:
    from rptg._types import Answer, Config, Json, Strings


def check(state: Json, answer: Answer, cfg: Config) -> Strings:
    """Строки кода — физические без документации (своей и вложенных функций), комментариев и
    пустых — не больше 2·D_код + S + 10; при объявленном D ещё D_код ≤ 1,5·D + 5. Договор —
    cfg.contracts[узел:операция]. Ручной max_lines узла — по физическим строкам; сложность блока
    ≤ max_complexity. Ручные назначения — по маскам §6.6: точный путь сильнее маски с большим
    числом буквальных сегментов, та — уровня, при равенстве побеждает позднее. Ответ не функция,
    не извлечён или без своего def — пусто: это покажут извлечение и правила."""
    if answer.kind != "function" or not answer.ok:
        return []
    try:
        tree = ast.parse(answer.code)
    except SyntaxError:
        return []
    fn = {s.name: s for s in tree.body if isinstance(s, ast.FunctionDef)}.get(answer.op)
    if fn is None:
        return []
    node = answer.node

    def blocks(f):
        return [(f.name, f.complexity)] + [b for c in f.closures for b in blocks(c)]

    def code_lines():
        docs = [n.body[0] for n in ast.walk(fn) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and ast.get_docstring(n) is not None]
        skip = {i for d in docs for i in range(d.lineno, d.end_lineno + 1)}
        text = answer.code.splitlines()[fn.lineno - 1:fn.end_lineno]
        return sum(1 for i, s in enumerate(text, fn.lineno) if s.strip()[:1] not in ("", "#") and i not in skip)

    def rank(mask):
        base, _, tail = mask.rpartition(".")
        if mask.startswith("level:"):
            lo, _, hi = mask[6:].partition("..")
            return 0 if int(lo) <= node.count(".") + 1 <= int(hi or lo) else -1
        inside = {"**": node == base or node.startswith(base + "."),
                  "*": node.startswith(base + ".") and node.count(".") == base.count(".") + 1}
        return base.count(".") + 1 if inside.get(tail) else 1000 if mask == node else -1

    def manual():
        found = sorted((r, i, ov) for i, (mask, ov) in enumerate(cfg.overrides.items()) if (r := rank(mask)) >= 0)
        own = {"max_complexity": cfg.limits.max_complexity}
        for _, _, ov in found:
            own.update({k: v for k, v in (("max_lines", ov.max_lines), ("max_complexity", ov.max_complexity)) if v})
        return own

    def contract():
        c = (cfg.contracts or {}).get(f"{node}:{answer.op}")
        return (c.sequence or 0, c.decisions) if c else (0, None)

    def problems(measured):
        realized, (sequence, declared), own, lines = sum(cc - 1 for _, cc in measured), contract(), manual(), code_lines()
        limit, physical = 2 * realized + sequence + 10, fn.end_lineno - fn.lineno + 1
        out = [f"{fn.name}: строк кода {lines}, предел 2·{realized} + {sequence} + 10 = {limit}"] if lines > limit else []
        if declared is not None and realized > 1.5 * declared + 5:
            out.append(f"{fn.name}: решений в коде {realized}, по договору {declared} — больше 1,5·D + 5 = {1.5 * declared + 5:g}: договор занижен или код раздут")
        if physical > own.get("max_lines", physical):
            out.append(f"{fn.name}: строк {physical}, ручной предел {own['max_lines']}")
        return out + [f"{fn.name}: сложность блока {name} — {cc}, предел {own['max_complexity']}"
                      for name, cc in measured if cc > own["max_complexity"]]

    return problems(blocks({f.name: f for f in cc_visit(answer.code)}[fn.name]))
