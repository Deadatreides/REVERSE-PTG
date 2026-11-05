"""Контрольные случаи затравки Э1 — tools/leafcheck0.py (норма трёх видов, arch1 WORK_PLAN этап 3).

Верный лист проходит без замечаний; каждый заведомо неверный — ловится с узнаваемой причиной;
правило, которое к листу неприменимо (open при объявленном эффекте fs.read), молчит. Числа
сложности сверяются с таблицей radon из его документации — не с выводом самой проверки.

    python -m pytest tests/test_leafcheck_controls.py -q
"""
import ast
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import leafcheck0 as lc  # noqa: E402

LIMITS = {"final_max_lines": 60, "max_complexity": 12}
CARD = {"id": "app.demo", "allowed_imports": ["json"], "effects": [],
        "ops": [{"name": "total", "params": [{"name": "xs", "type": "Ints"}, {"name": "k", "type": "integer"}],
                 "result": "integer"}]}
GOOD = '''
"""Лист app.demo."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app._types import Ints


def total(xs: Ints, k: int) -> int:
    """Сумма, умноженная на k."""
    return sum(xs) * k + len(json.dumps(xs)) * 0
'''


def check(tmp_path, source, card=CARD, limits=LIMITS, override=None, contracts=None):
    path = tmp_path / "demo.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    problems, _, _ = lc.check_leaf(card, path, limits, override or {}, contracts)
    return problems


def test_good_leaf_passes(tmp_path):
    assert check(tmp_path, GOOD) == []


@pytest.mark.parametrize("old, new, why", [
    ("import json\n", "import json\nimport os\n", "импорт os"),
    ("return sum(xs) * k", "return eval('1') + sum(xs) * k", "запрещённый вызов eval"),
    ("return sum(xs) * k", "return len(xs.__class__.__name__) + sum(xs) * k", "доступ к __class__"),
    ("def total(xs: Ints, k: int) -> int:", "def total(k: int, xs: Ints) -> int:", "параметры"),
    ("def total(xs: Ints, k: int) -> int:", "def total(xs, k: int) -> int:", "аннотация xs"),
    ("def total(xs: Ints, k: int) -> int:", "def total(xs: Ints, k: int) -> float:", "аннотация результата"),
    ("\n\ndef total(", "\n\ndef helper():\n    return 1\n\n\ndef total(", "на верхнем уровне"),
    ("def total(", "def other(", "нет def total"),
    ("return sum(xs) * k", "return len(open('x').read()) + sum(xs) * k", "запрещённый вызов open"),
])
def test_bad_leaf_is_caught(tmp_path, old, new, why):
    assert GOOD.count(old) == 1
    problems = check(tmp_path, GOOD.replace(old, new))
    assert any(why in p for p in problems), problems


BRANCHES = "\n".join(f"    if k == {i}:\n        return {i}" for i in range(13))   # 13 решений, 26 строк
STRAIGHT = "\n".join(f"    k = k + {i}" for i in range(20))                           # 0 решений, 20 строк


def with_body(body):
    return GOOD.replace('    """Сумма, умноженная на k."""\n', '    """Сумма."""\n' + body + "\n")


def test_complexity_limit_per_block(tmp_path):
    problems = check(tmp_path, with_body(BRANCHES))
    assert any("сложность блока total — 14" in p for p in problems), problems
    assert check(tmp_path, with_body(BRANCHES), override={"max_complexity": 20}) == []


def test_verbose_code_breaks_the_line_function(tmp_path):
    # 20 прямолинейных строк без решений: строк кода 22 при пределе 2·0 + 0 + 10 = 10
    problems = check(tmp_path, with_body(STRAIGHT))
    assert any("строк кода 22, предел 2·0 + 0 + 10 = 10" in p for p in problems), problems


def test_branches_pay_for_their_lines(tmp_path):
    # 13 решений на 26 строках — ровно закон «две строки на решение»: предел 2·13 + 10 = 36
    assert check(tmp_path, with_body(BRANCHES), override={"max_complexity": 20}) == []


def test_documentation_and_blank_lines_are_free(tmp_path):
    doc = '    """Сумма.\n\n' + "\n".join("    Строка пояснения." for _ in range(40)) + '\n    """\n'
    source = GOOD.replace('    """Сумма, умноженная на k."""\n', doc + "\n\n    # комментарий\n")
    assert check(tmp_path, source) == []


def test_contract_sequence_allows_straight_code(tmp_path):
    # неприменимость: прямолинейные шаги, которых требует договор (S = 20), не многословие
    assert check(tmp_path, with_body(STRAIGHT), contracts={"total": {"sequence": 20}}) == []


def test_decisions_beyond_the_contract_are_caught(tmp_path):
    # 13 решений при договорных 2: больше 1,5·2 + 5 = 8 — код раздут или договор занижен
    problems = check(tmp_path, with_body(BRANCHES), override={"max_complexity": 20},
                     contracts={"total": {"decisions": 2}})
    assert any("решений в коде 13, по договору 2" in p for p in problems), problems
    assert check(tmp_path, with_body(BRANCHES), override={"max_complexity": 20},
                 contracts={"total": {"decisions": 10}}) == []


def test_explicit_manual_line_limit_still_applies(tmp_path):
    over = check(tmp_path, GOOD, override={"max_lines": 2})  # функция — 3 физические строки
    assert any("строк 3, ручной предел 2" in p for p in over), over


def test_open_rule_is_inapplicable_with_fs_effect(tmp_path):
    card = {**CARD, "effects": ["fs.read"]}
    source = GOOD.replace("return sum(xs) * k", "return len(open('x').read()) + sum(xs) * k")
    assert check(tmp_path, source, card=card) == []


def test_own_table_equals_radon_on_every_leaf_block():
    # запасная таблица обязана давать то же, что radon: без radon проверка не должна менять вердикт
    pytest.importorskip("radon")
    blocks = 0
    for path in sorted((ROOT / "rptg").rglob("*.py")):
        if path.name.startswith("_") or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        theirs = lc.radon_blocks(text)
        for fn in ast.parse(text).body:
            if isinstance(fn, ast.FunctionDef):
                assert sorted(lc.complexity(fn)) == sorted(theirs[fn.name]), f"{path.name}:{fn.name}"
                blocks += len(theirs[fn.name])
    assert blocks >= 100


@pytest.mark.parametrize("source, want", [
    # таблица radon: 1 + if + and + for + if + with + 2 except + генератор + if в генераторе = 10
    ('''
def f(a, b):
    if a and b:
        return 1
    for x in a:
        if x:
            pass
    with ctx(a):
        pass
    try:
        pass
    except ValueError:
        pass
    except KeyError:
        pass
    return [y for y in b if y]
''', [("f", 10)]),
    # вложенная функция — отдельный блок; условное выражение +1
    ('''
def f(x):
    def g(y):
        if y:
            return 1
        return 0
    return g(x) if x else 0
''', [("f", 2), ("g", 2)]),
    # лямбда считается в своём блоке; else и finally — 0
    ('''
def f(x):
    k = lambda v: 1 if v else 0
    try:
        pass
    finally:
        pass
    if x:
        pass
    else:
        pass
    return k(x)
''', [("f", 3)]),
])
def test_complexity_follows_radon_table(source, want):
    fn = ast.parse(textwrap.dedent(source)).body[0]
    assert lc.complexity(fn) == want
