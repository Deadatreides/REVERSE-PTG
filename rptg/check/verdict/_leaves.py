"""Финальные дети узла rptg.check.verdict в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.check.verdict.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import applied as _m_applied
from . import content as _m_content
from . import order as _m_order
from . import accept as _m_accept
from . import report as _m_report

if TYPE_CHECKING:
    from rptg._types import Acceptance, Answer, Config, Evidence, Evidences, Json, Report, Sha
    from rptg.check._types import Parts, SubjectRef
    from rptg.check.verdict._types import Applied, Needed, Shas



class applied:
    """Лист rptg.check.verdict.applied: операции в обёртках условий."""

    @staticmethod
    def apply(state: Json, event: Json, answer: Answer) -> Applied:
        """разложение — в designs[узел], его типы — в types; функция — в code[узел:операция]; карта — map_text, карточка корня, типы корня; предмет — предмет ответа, у прогона — предмет цели; ответ не извлечён — raw = сырой текст"""
        result = _m_applied.apply(state=state, event=event, answer=answer)
        return result


class content:
    """Лист rptg.check.verdict.content: операции в обёртках условий."""

    @staticmethod
    def of(state: Json, subject: str, raw: Json) -> Needed:
        """raw не null — содержимое сам raw; разложение X — само разложение, карточка X, карточки uses X, типы строгих предков X; функция — код, операция без имени, используемые типы по ссылкам, импорты и эффекты узла; сборка X — содержимое разложения X и детей (функций и сборок), а в more — разложение X и все предметы поддерева; карта — ответ карты и примеры пользователя; неизвестный предмет — пустой объект"""
        result = _m_content.of(state=state, subject=subject, raw=raw)
        _c.check('rptg.check.verdict.content:of', 'ensures', [
            ('result.main.subject == subject', lambda: (result.main.subject == subject)),
        ])
        return result


class order:
    """Лист rptg.check.verdict.order: операции в обёртках условий."""

    @staticmethod
    def assemble(parts: Parts, subject: SubjectRef, digest: Sha, cfg: Config) -> Evidences:
        """доказательства слоёв в порядке P1 P2 P3 P4 P5 P7 E1 E2 E3 E6; после провала П1 остальные отбрасываются; ставятся предмет, хэш, HARD и доверие по cfg.trusted"""
        result = _m_order.assemble(parts=parts, subject=subject, digest=digest, cfg=cfg)
        _c.check('rptg.check.verdict.order:assemble', 'ensures', [
            ('forall e in result: e.hard', lambda: all(e.hard for e in result)),
            ('forall e in result: e.subject_hash == digest', lambda: all((e.subject_hash == digest) for e in result)),
            ('forall e in result: e.subject == subject.subject', lambda: all((e.subject == subject.subject) for e in result)),
        ])
        return result


class accept:
    """Лист rptg.check.verdict.accept: операции в обёртках условий."""

    @staticmethod
    def judge(state: Json, needed: Needed, main: Sha, more: Shas) -> Acceptance:
        """требуемые слои: разложение — P1 P2 P3 P4 P7, функция — E1 E2 E3, сборка — E6, карта — P1 P4 P7; слой есть, если на хэше предмета есть HARD pass доверенной проверки и нет HARD fail или unknown; missing — недостающие слои предмета и всех предметов more, по порядку слоёв без повторов"""
        _c.check('rptg.check.verdict.accept:judge', 'requires', [
            ('len(more) == len(needed.more)', lambda: (len(more) == len(needed.more))),
        ])
        result = _m_accept.judge(state=state, needed=needed, main=main, more=more)
        _c.check('rptg.check.verdict.accept:judge', 'ensures', [
            ('result.accepted == (len(result.missing) == 0)', lambda: (result.accepted == (len(result.missing) == 0))),
        ])
        return result


class report:
    """Лист rptg.check.verdict.report: операции в обёртках условий."""

    @staticmethod
    def report(evidence: Evidence, state: Json) -> Report:
        """правило, место, фрагмент, ожидание — из details (нет — по слою: правило — сам слой, место — предмет, ожидание — причина); контрпример — из доказательства; смысл — по правилу из таблицы"""
        _c.check('rptg.check.verdict.report:report', 'requires', [
            ('evidence.verdict == "fail"', lambda: (evidence.verdict == "fail")),
        ])
        result = _m_report.report(evidence=evidence, state=state)
        _c.check('rptg.check.verdict.report:report', 'ensures', [
            ('result.subject == evidence.subject', lambda: (result.subject == evidence.subject)),
            ('result.layer == evidence.check', lambda: (result.layer == evidence.check)),
        ])
        return result
