"""Финальные дети узла rptg.views в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.views.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import status as _m_status
from . import node as _m_node
from . import graph as _m_graph
from . import outcomes as _m_outcomes
from . import pick as _m_pick

if TYPE_CHECKING:
    from rptg._types import Json, View, ViewQuery
    from rptg.views._types import NodeAcceptances, NodeSubjects



class status:
    """Лист rptg.views.status: операции в обёртках условий."""

    @staticmethod
    def count(state: Json) -> Json:
        """фаза, узлов (карточек), элементов принято и запланировано (состояние planned), расход и лимит бюджета — ровно эти поля"""
        result = _m_status.count(state=state)
        return result


class node:
    """Лист rptg.views.node: операции в обёртках условий."""

    @staticmethod
    def subjects(state: Json, query: ViewQuery) -> NodeSubjects:
        """предметы элементов узла запроса (map, design, function, assembly этого узла) по порядку предметов"""
        result = _m_node.subjects(state=state, query=query)
        return result

    @staticmethod
    def view(state: Json, query: ViewQuery, subjects: NodeSubjects, acceptances: NodeAcceptances) -> Json:
        """узел запроса: карточка или null, разложение (дети и операции схем) или null, элементы по порядку предметов — состояние, оператор, ступень и источник назначения (нет — пустые), попытки, повторы формы, токены, цена, отчёты, причина ожидания пользователя (нет — пусто), принят ли и каких слоёв не хватает"""
        _c.check('rptg.views.node:view', 'requires', [
            ('len(acceptances) == len(subjects)', lambda: (len(acceptances) == len(subjects))),
        ])
        result = _m_node.view(state=state, query=query, subjects=subjects, acceptances=acceptances)
        return result


class graph:
    """Лист rptg.views.graph: операции в обёртках условий."""

    @staticmethod
    def build(state: Json) -> Json:
        """узлы — карточки по порядку id: родитель (у корня пусто); вид — составной (есть разложение или его элемент), финальный (есть элементы функций), иначе pending; оператор и источник — назначения разложения у составного, первой функции у финального (нет — пусто). Рёбра — child от родителя по порядку узлов, затем uses от узла к используемому"""
        result = _m_graph.build(state=state)
        return result

    @staticmethod
    def paint(state: Json, graph: Json) -> Json:
        """цвет узла по его элементам (Э1 04.10.2026: вторая работа graph): suspect — элемент под подозрением; failed — элемент ждёт пользователя; accepted — у составного принята сборка, у финального есть функции и все приняты; working — элемент сдвинулся с planned; иначе planned. Узлы — с полем status, рёбра — как есть"""
        result = _m_graph.paint(state=state, graph=graph)
        return result


class outcomes:
    """Лист rptg.views.outcomes: операции в обёртках условий."""

    @staticmethod
    def rows(state: Json) -> Json:
        """пометка «не для сравнения операторов» и строки по (род, оператор) назначения элементов в порядке рода и оператора: задач, принято, попыток, токенов, цена — сумма записей в масштабе самой длинной (модуль decimal узлу не разрешён — в целых); элементы без назначения не считаются"""
        result = _m_outcomes.rows(state=state)
        return result


class pick:
    """Лист rptg.views.pick: операции в обёртках условий."""

    @staticmethod
    def view(query: ViewQuery, status: Json, node: Json, graph: Json, competence: Json) -> View:
        """вид запроса и данные его представления"""
        result = _m_pick.view(query=query, status=status, node=node, graph=graph, competence=competence)
        _c.check('rptg.views.pick:view', 'ensures', [
            ('result.kind == query.kind', lambda: (result.kind == query.kind)),
        ])
        return result
