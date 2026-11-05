"""Финальные дети узла rptg.lang.cl.logic в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.lang.cl.logic.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import smt as _m_smt
from . import schema as _m_schema
from . import script as _m_script
from . import solve as _m_solve
from . import decode as _m_decode

if TYPE_CHECKING:
    from rptg._types import Limits, Proof, Sat, TypeEnv
    from rptg.lang.cl._types import Typed
    from rptg.lang.cl.logic._types import SmtTerm, SmtTerms, SmtText, SolveResult



class smt:
    """Лист rptg.lang.cl.logic.smt: операции в обёртках условий."""

    @staticmethod
    def term(typed: Typed, limits: Limits) -> SmtTerm:
        """формула условия и сорта её символов; факты типов пусты — их добавляет schema"""
        result = _m_smt.term(typed=typed, limits=limits)
        _c.check('rptg.lang.cl.logic.smt:term', 'ensures', [
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
            ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
            ('not typed.ok => not result.ok', lambda: ((not (not typed.ok)) or (not result.ok))),
            ('len(result.facts) == 0', lambda: (len(result.facts) == 0)),
        ])
        return result


class schema:
    """Лист rptg.lang.cl.logic.schema: операции в обёртках условий."""

    @staticmethod
    def facts(term: SmtTerm, env: TypeEnv, limits: Limits) -> SmtTerm:
        """факты каждого символа формулы по его схеме; у необязательного значения — под признаком |p?|"""
        result = _m_schema.facts(term=term, env=env, limits=limits)
        _c.check('rptg.lang.cl.logic.schema:facts', 'ensures', [
            ('result.term == term.term', lambda: (result.term == term.term)),
            ('result.ok == term.ok', lambda: (result.ok == term.ok)),
            ('len(result.facts) >= len(term.facts)', lambda: (len(result.facts) >= len(term.facts))),
        ])
        return result


class script:
    """Лист rptg.lang.cl.logic.script: операции в обёртках условий."""

    @staticmethod
    def prove(facts: SmtTerms, goal: SmtTerm, limits: Limits) -> SmtText:
        """факты и отрицание цели: «невыполнимо» значит «доказано»"""
        result = _m_script.prove(facts=facts, goal=goal, limits=limits)
        _c.check('rptg.lang.cl.logic.script:prove', 'ensures', [
            ('result.bound == limits.k_lists', lambda: (result.bound == limits.k_lists)),
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
            ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
        ])
        return result

    @staticmethod
    def sat(conds: SmtTerms, limits: Limits) -> SmtText:
        """условия под именами c0, c1, … — для ядра противоречия"""
        result = _m_script.sat(conds=conds, limits=limits)
        _c.check('rptg.lang.cl.logic.script:sat', 'ensures', [
            ('result.bound == limits.k_lists', lambda: (result.bound == limits.k_lists)),
            ('result.ok => len(result.errors) == 0', lambda: ((not result.ok) or (len(result.errors) == 0))),
            ('not result.ok => len(result.errors) >= 1', lambda: ((not (not result.ok)) or (len(result.errors) >= 1))),
        ])
        return result


class solve:
    """Лист rptg.lang.cl.logic.solve: операции в обёртках условий."""

    @staticmethod
    def run(smt: SmtText, limits: Limits) -> SolveResult:
        """решить текст SMT-LIB; неготовый текст или отсутствие z3 — unknown с причиной"""
        result = _m_solve.run(smt=smt, limits=limits)
        _c.check('rptg.lang.cl.logic.solve:run', 'ensures', [
            ('result.status == "unsat" => len(result.model) == 0', lambda: ((not (result.status == "unsat")) or (len(result.model) == 0))),
        ])
        return result


class decode:
    """Лист rptg.lang.cl.logic.decode: операции в обёртках условий."""

    @staticmethod
    def proof(answer: SolveResult, smt: SmtText, limits: Limits) -> Proof:
        """unsat → доказано; sat → опровергнуто, контрпример — значения всех символов модели: и цели, и фактов (LOGIC §5 П4 — в нём значения параметров операции, а они есть только в фактах); иначе неизвестно"""
        result = _m_decode.proof(answer=answer, smt=smt, limits=limits)
        _c.check('rptg.lang.cl.logic.decode:proof', 'ensures', [
            ('result.verdict == "refuted" => result.counterexample != null', lambda: ((not (result.verdict == "refuted")) or (result.counterexample is not None))),
            ('result.bound == limits.k_lists', lambda: (result.bound == limits.k_lists)),
        ])
        return result

    @staticmethod
    def sat(answer: SolveResult, smt: SmtText) -> Sat:
        """sat → выполнимо; unsat → номера строк ядра; иначе неизвестно"""
        result = _m_decode.sat(answer=answer, smt=smt)
        _c.check('rptg.lang.cl.logic.decode:sat', 'ensures', [
            ('result.verdict == "unsat" => len(result.core) >= 1', lambda: ((not (result.verdict == "unsat")) or (len(result.core) >= 1))),
        ])
        return result
