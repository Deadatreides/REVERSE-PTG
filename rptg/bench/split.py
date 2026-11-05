"""Лист rptg.bench.split — раздел эталонного набора на подбор и проверку (LOGIC §6.4).

Функция принята по карточке design/rptg.bench.yaml; обвязку пишет скрипт. Хэши имён задач даёт lang в
схеме — модуль hashlib узлу не разрешён. Раздел фиксирован до прогона и от исходов не зависит: в
experiment14 — по зерну, в ядре rptg случайности нет. Порядок — род, затем хэш (К-8, утверждено
02.10.2026): в experiment14 каждая задача несла все роды и раздел делил их поровну, у задачи rptg один
род, и общий порядок по хэшу делил роды неровно.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg.bench._types import Halves

if TYPE_CHECKING:
    from rptg._types import ReferenceSet
    from rptg.bench._types import Digests


def halves(reference: ReferenceSet, digests: Digests) -> Halves:
    """Задачи набора по роду, внутри рода — по возрастанию хэша имени (digests — хэши имён по порядку
    набора), равные хэши — по имени; чётные места общего списка — подбор, нечётные — проверка: каждый род
    делится поровну, ±1."""
    keys = zip((item.class_ for item in reference.items), digests, (item.id for item in reference.items))
    order = [name for _, _, name in sorted(keys)]
    return Halves(fit=order[0::2], check=order[1::2])
