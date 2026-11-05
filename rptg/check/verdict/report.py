"""Лист rptg.check.verdict.report — отчёт о нарушении по шаблону (LOGIC §8.4).

Функции приняты по карточке design/rptg.check.verdict.yaml; обвязку пишет скрипт. Отчёт одинаков
для любой модели и самодостаточен: место, фрагмент и ожидание кладёт в details сама проверка, когда
у неё под рукой предмет, — отчёт их только переносит.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg._types import Report

if TYPE_CHECKING:
    from rptg._types import Evidence, Json


def report(evidence: Evidence, state: Json) -> Report:
    """Правило, место, фрагмент, ожидание — из details; чего нет — по слою: правило — сам слой,
    место — предмет, ожидание — причина. Контрпример — из доказательства, смысл — по правилу."""
    means = {
        "I12": "тип источника не подходит месту назначения",
        "I13": "требование вызываемой операции не гарантировано выше по потоку",
        "I14": "условия операции противоречат друг другу",
        "I15": "примеров меньше, чем требует метод",
        "I16": "пример нарушает типы или условия своей операции",
        "P1": "ответ не прошёл проверку формы",
        "P2": "нарушен инвариант графа",
        "E1": "код функции нарушает правила статики",
        "E2": "функция не выполнила пример",
        "E3": "функция нарушила гарантию на сгенерированном входе",
        "E6": "собранный узел не выполнил пример или свойство",
    }
    details = evidence.details if isinstance(evidence.details, dict) else {}
    rule = details.get("rule") or evidence.check
    return Report(subject=evidence.subject, layer=evidence.check, rule=rule,
                  where=details.get("where") or evidence.subject, fragment=details.get("fragment"),
                  expected=details.get("expected") or details.get("reason") or "",
                  counterexample=evidence.counterexample,
                  means=means.get(rule) or means.get(evidence.check) or "")
