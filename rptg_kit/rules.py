"""Правила из карточек — в настройки готовых принудителей: tach.toml (кто кого может импортировать — как
ArchUnit, только для Python), pyproject.toml (mypy strict, ruff с запретами API, pytest с doctest) и
tests/test_rptg_cases.py (deal.cases — тесты на свойства из условий карточки). Настройки остаются в программе:
границы держатся и после того, как kit закончил.
"""
import ast
import json
import re

from . import cards
from .project import module_of

IO_RE = re.compile(r"^\s*effects:\s*io\s*$", re.M)

# Запреты для модулей без объявленных побочных эффектов (ruff TID251); модуль с «effects: io» в описании их снимает.
BANNED = {"os": "файловая система и процессы — только в узле с effects: io", "subprocess": "процессы — только в узле с effects: io",
          "socket": "сеть — только в узле с effects: io", "shutil": "файловая система — только в узле с effects: io",
          "urllib": "сеть — только в узле с effects: io", "http": "сеть — только в узле с effects: io",
          "ctypes": "машинный код — не допускается", "importlib": "динамический импорт — не допускается"}


def pyproject(package, io_modules=(), deps=(), imports=()):
    """deps — пакеты, которые импортирует программа (имена дистрибутивов), сверх deal; imports — их имена модулей:
    mypy не требует от них заглушек типов (у networkx, scipy их нет), типизированные проверяются как обычно."""
    banned = "\n".join(f'"{name}".msg = "{msg}"' for name, msg in BANNED.items())
    ignores = "\n".join(f'"{m.replace(".", "/")}{tail}" = ["TID251", "T20"]' for m in sorted(io_modules) for tail in (".py", "/**"))
    dependencies = json.dumps(["deal", *sorted(set(deps) - {"deal"})], ensure_ascii=False)
    loose = sorted(set(imports) - {"deal"})
    overrides = "" if not loose else (
        "\n[[tool.mypy.overrides]]\nmodule = " + json.dumps([x for m in loose for x in (m, m + ".*")], ensure_ascii=False)
        + "\nignore_missing_imports = true\n")
    return f'''[project]
name = "{package}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = {dependencies}

[tool.setuptools.packages.find]
include = ["{package}*"]

[tool.mypy]
strict = true
{overrides}
[tool.ruff]
line-length = 140

[tool.ruff.lint]
select = ["E", "F", "B", "C90", "TID251", "S", "T20"]
ignore = ["E501", "S101", "F401"]  # F401: импорты карточки объявляют зависимости до того, как их вызовет код

[tool.ruff.lint.mccabe]
max-complexity = 20

[tool.ruff.lint.flake8-tidy-imports.banned-api]
{banned}

[tool.ruff.lint.per-file-ignores]
{ignores}

[tool.pytest.ini_options]
addopts = "--doctest-modules -q -p no:cacheprovider"
testpaths = ["{package}", "tests"]
'''


def io_modules(files):
    """Модули, где ТЗ разрешает ввод-вывод: строка «effects: io» в описании модуля."""
    out = []
    for rel, text in files.items():
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            continue
        if IO_RE.search(doc):
            out.append(module_of(rel))
    return sorted(out)


def graph(files, package):
    """Модуль → модули своего пакета, которые он импортирует (по текстам файлов {путь: текст})."""
    known = {module_of(rel) for rel in files}
    return {module_of(rel): sorted(cards.resolve(cards.imports(text, package), known) - {module_of(rel)}) for rel, text in files.items()}


def tach_toml(deps):
    """tach.toml из графа: у каждого модуля — ровно те зависимости, что объявила его карточка; циклы запрещены."""
    blocks = [f'[[modules]]\npath = "{m}"\ndepends_on = {json.dumps(sorted(d))}\n' for m, d in sorted(deps.items())]
    return 'source_roots = ["."]\nforbid_circular_dependencies = true\n\n' + "\n".join(blocks)


CASES_RUNNER = '''
# Настройки deal по умолчанию, и сверх них сняты порог «медленная генерация» и срок на вызов. Условие pre,
# связывающее аргументы (0 <= start < end <= len(text)), отсекает почти все случайные входы; проверка идёт на тех,
# что прошли (11.10, memcore.scrubbing: 7 годных из 350 — Hypothesis бросал проверку по порогу). Снят и порог
# «большие входы»: вложенные записи (карточка со связями и пометками) его превышают через раз, и тест падал без
# дефекта (13.10, ptgcore.context.block.render_block: 9 годных из 29).
SETTINGS = hypothesis.settings(database=None, max_examples=50, deadline=None, verbosity=hypothesis.Verbosity.quiet,
                               report_multiple_bugs=False, print_blob=True,
                               suppress_health_check=[hypothesis.HealthCheck.filter_too_much, hypothesis.HealthCheck.too_slow,
                                                      hypothesis.HealthCheck.data_too_large])


def cases(func):
    """deal.cases для функции. Ни одного входа, который допускают условия pre (Unsatisfiable), — пропуск с причиной:
    свойства такой функции проверяет CrossHair, он решает условия, а не перебирает входы."""
    test = deal.cases(func, settings=SETTINGS)

    def run():
        try:
            test()
        except hypothesis.errors.Unsatisfiable:
            pytest.skip("условия pre отсекли все случайные входы — свойства этой функции проверяет CrossHair")
    return run
'''


CONFTEST = '''"""Пишет rptg kit. Каждый пример и тест идёт в чистой папке с копией tests/fixtures: базы и файлы, которые пишут
примеры функций с effects: io, не остаются в проекте, и повторный `pytest` даёт тот же итог, что проверки kit на
свежей копии программы."""
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


@pytest.fixture(autouse=True)
def _rptg_clean_dir(tmp_path, monkeypatch):
    fixtures = ROOT / "tests" / "fixtures"
    if fixtures.is_dir():
        shutil.copytree(fixtures, tmp_path / "tests" / "fixtures")
    monkeypatch.chdir(tmp_path)
'''


def cases_test(package, functions):
    """tests/test_rptg_cases.py: deal.cases для каждой написанной функции — сотни входов, которые допускают
    условия pre, и проверка ensure на каждом (Hypothesis)."""
    lines = ['"""Тесты на свойства из условий карточек: deal.cases (Hypothesis). Пишет rptg kit."""', "import sys", "",
             "import deal", "import hypothesis", "import pytest", ""]
    modules = sorted({f.split(":")[0] for f in functions})
    lines += [f"import {m}" for m in modules] + [CASES_RUNNER]
    # Модуль — через sys.modules, а не цепочкой атрибутов: родитель вправе связать функцию с именем ребёнка
    # (from graphlm.laws.capacity import capacity), и тогда graphlm.laws.capacity — уже функция (16.10, graphlm).
    for f in sorted(functions):
        module, name = f.split(":")
        lines.append(f"test_{module.replace('.', '_')}__{name} = cases(sys.modules[{module!r}].{name})")
    return "\n".join(lines) + "\n"


def case_id(function):
    module, name = function.split(":")
    return f"tests/test_rptg_cases.py::test_{module.replace('.', '_')}__{name}"
