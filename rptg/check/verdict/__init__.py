"""итог по доказательствам: предмет и содержимое его хэша (LOGIC §10), сборка доказательств в порядке слоёв с хэшем и доверием, правило приёмки, отчёт о нарушении

Сгенерировано tools/codegen0.py по design/rptg.check.verdict.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c

from . import _flows

if TYPE_CHECKING:
    from rptg._types import Acceptance, Answer, Config, Evidence, Evidences, Json, Report, Sha, Subject
    from rptg.check._types import Parts, SubjectRef



def subject(state: Json, event: Json, answer: Answer) -> SubjectRef:
    """предмет события и содержимое H(x): разложение — само разложение, карточка узла, карточки uses, типы владельцев-предков; карта — ответ и примеры пользователя; функция — код, операция без имени, её типы, импорты и эффекты узла; сборка — разложение и принятые дети; неизвлечённый ответ — его сырой текст"""
    result = _flows.subject(state=state, event=event, answer=answer)
    _c.check('rptg.check.verdict:subject', 'ensures', [
        ('result.subject == answer.subject or answer.kind == "none"', lambda: ((result.subject == answer.subject) or (answer.kind == "none"))),
    ])
    return result


def assemble(parts: Parts, subject: SubjectRef, digest: Sha, cfg: Config) -> Evidences:
    """доказательства слоёв в порядке P1 P2 P3 P4 P5 P7 E1 E2 E3 E6; после провала П1 остальные слои отбрасываются; ставятся предмет, хэш, HARD и доверие по cfg.trusted"""
    result = _flows.assemble(parts=parts, subject=subject, digest=digest, cfg=cfg)
    _c.check('rptg.check.verdict:assemble', 'ensures', [
        ('forall e in result: e.hard', lambda: all(e.hard for e in result)),
        ('forall e in result: e.subject_hash == digest', lambda: all((e.subject_hash == digest) for e in result)),
        ('forall e in result: e.subject == subject.subject', lambda: all((e.subject == subject.subject) for e in result)),
    ])
    return result


def accepted(state: Json, subject: Subject) -> Acceptance:
    """принят ли предмет (LOGIC §10): для каждого требуемого слоя есть HARD pass от доверенной проверки на текущем хэше и нет HARD fail или unknown на нём же; сборка — ещё принятое разложение и принятые дети"""
    result = _flows.accepted(state=state, subject=subject)
    _c.check('rptg.check.verdict:accepted', 'ensures', [
        ('result.accepted => len(result.missing) == 0', lambda: ((not result.accepted) or (len(result.missing) == 0))),
    ])
    return result


def report(evidence: Evidence, state: Json) -> Report:
    """доказательство провала → самодостаточный отчёт для починки по шаблону: место, фрагмент, ожидание и контрпример — из details, смысл — по правилу"""
    _c.check('rptg.check.verdict:report', 'requires', [
        ('evidence.verdict == "fail"', lambda: (evidence.verdict == "fail")),
    ])
    result = _flows.report(evidence=evidence, state=state)
    _c.check('rptg.check.verdict:report', 'ensures', [
        ('result.subject == evidence.subject', lambda: (result.subject == evidence.subject)),
        ('result.layer == evidence.check', lambda: (result.layer == evidence.check)),
    ])
    return result
