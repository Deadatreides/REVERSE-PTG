"""rptg kit без моделей: ответы субагентов записаны, проверки — настоящие (mypy, tach, ruff, deal, Hypothesis,
CrossHair, radon). Запуск — интерпретатором окружения с готовыми проверками:

    .venv-kit\\Scripts\\python -m pytest tests/test_kit.py -q
"""
import asyncio
import json
import os
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

pytest.importorskip("deal")
pytest.importorskip("crosshair")
pytest.importorskip("tach")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rptg_kit import cards, checks, connect, rules, server  # noqa: E402
from rptg_kit.project import Project  # noqa: E402

TYPES = '''"""Типы накладной."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    """Деньги в минимальных единицах валюты."""

    amount: int
    currency: str


@dataclass(frozen=True)
class Line:
    """Строка накладной."""

    qty: int
    price: Money
'''

PRE_LINES = '''@deal.pre(lambda lines: len(lines) >= 1 and all(x.qty > 0 and x.price.amount >= 0 for x in lines))
@deal.pre(lambda lines: all(x.price.currency == lines[0].price.currency for x in lines))
@deal.ensure(lambda lines, result: result.currency == lines[0].price.currency and result.amount >= 0)
@deal.has()'''

ROOT_MODULE = f'''"""Накладные: итог по строкам.

node: composite
"""
import deal

from inv.billing import total
from inv.types import Line, Money


{PRE_LINES}
def invoice_total(lines: list[Line]) -> Money:
    """Итог накладной.

    D: 1

    >>> invoice_total([Line(2, Money(150, "KZT")), Line(1, Money(50, "KZT"))])
    Money(amount=350, currency='KZT')
    >>> invoice_total([Line(1, Money(0, "USD"))])
    Money(amount=0, currency='USD')
    """
    return total(lines)
'''

MONEY = '''"""Деньги одной валюты.

node: leaf
"""
import deal

from inv.types import Money


@deal.pre(lambda a, b: a.currency == b.currency)
@deal.ensure(lambda a, b, result: result.amount == a.amount + b.amount and result.currency == a.currency)
@deal.has()
def add(a: Money, b: Money) -> Money:
    """Сумма двух денег одной валюты.

    D: 1

    >>> add(Money(100, "KZT"), Money(50, "KZT"))
    Money(amount=150, currency='KZT')
    >>> add(Money(0, "USD"), Money(7, "USD"))
    Money(amount=7, currency='USD')
    """
    raise NotImplementedError
'''

BILLING_DOC = '''    """Итог по строкам.

    D: 2

    >>> total([Line(2, Money(150, "KZT")), Line(1, Money(50, "KZT"))])
    Money(amount=350, currency='KZT')
    """'''

BILLING_CARD = f'''"""Строки и итог накладной.

node: composite
"""
import deal

from inv.money import add
from inv.types import Line, Money


{PRE_LINES}
def total(lines: list[Line]) -> Money:
{BILLING_DOC}
    raise NotImplementedError
'''

BILLING_WIRED = f'''"""Строки и итог накладной.

node: composite
"""
import deal

from inv.billing.lines import line_total
from inv.money import add
from inv.types import Line, Money


{PRE_LINES}
def total(lines: list[Line]) -> Money:
{BILLING_DOC}
    acc = line_total(lines[0])
    for line in lines[1:]:
        acc = add(acc, line_total(line))
    return acc
'''

LINES = '''"""Сумма строки накладной.

node: leaf
"""
import deal

from inv.types import Line, Money


@deal.pre(lambda line: line.qty > 0 and line.price.amount >= 0)
@deal.ensure(lambda line, result: result.amount == line.qty * line.price.amount and result.currency == line.price.currency)
@deal.has()
def line_total(line: Line) -> Money:
    """Сумма строки: количество × цена.

    D: 1

    >>> line_total(Line(2, Money(150, "KZT")))
    Money(amount=300, currency='KZT')
    >>> line_total(Line(1, Money(0, "USD")))
    Money(amount=0, currency='USD')
    """
    raise NotImplementedError
'''

ARCHITECTURE = {"inv/__init__.py": ROOT_MODULE, "inv/types.py": TYPES, "inv/money.py": MONEY, "inv/billing/__init__.py": BILLING_CARD}
ADD_BAD = "def add(a: Money, b: Money) -> Money:\n    return Money(a.amount - b.amount, a.currency)\n"
ADD_GOOD = "def add(a: Money, b: Money) -> Money:\n    return Money(a.amount + b.amount, a.currency)\n"
LT_GOOD = "def line_total(line: Line) -> Money:\n    return Money(line.qty * line.price.amount, line.price.currency)\n"


def new_project(tmp_path, seconds=3):
    out = server.kit_new(str(tmp_path / "app"), "inv", "накладные")
    assert out["ok"], out
    project = Project(tmp_path / "app")
    state = project.load()
    state["limits"]["crosshair_seconds"] = seconds
    project.save(state)
    return project


def ticket_of(answer, kind):
    return next(t["ticket"] for t in answer["tickets"] if t["kind"] == kind)


def approved(tmp_path):
    project = new_project(tmp_path)
    arch = server.kit_next(str(project.root))
    assert arch["kind"] == "architect"
    verdict = server.kit_submit(str(project.root), ticket_of(arch, "architect"), files=ARCHITECTURE)
    assert verdict["ok"], verdict["report"]
    assert server.kit_next(str(project.root))["kind"] == "approve"
    assert server.kit_approve(str(project.root), True)["ok"]
    return project


def test_invoice_program_from_architecture_to_done(tmp_path):
    """Корень → утверждение → разложение billing (sonnet) → код листьев (haiku: ошибка, починка по отчёту) → сборка
    составных с настоящими детьми → программа проходит свои тесты сама."""
    project = approved(tmp_path)
    work = server.kit_next(str(project.root))
    assert work["kind"] == "work"
    kinds = {t["target"]: (t["kind"], t["model"], t["agent"]) for t in work["tickets"]}
    assert kinds == {"inv.billing": ("design", "sonnet", "rptg-designer"), "inv.money": ("implement", "haiku", "rptg-implementer")}
    brief = server.kit_brief(str(project.root), ticket_of(work, "design"))
    assert "inv.billing" in brief and "ПРАВИЛА КАРТОЧЕК" in brief and "def add(a: Money, b: Money) -> Money:" in brief

    design = server.kit_submit(str(project.root), ticket_of(work, "design"),
                               files={"inv/billing/__init__.py": BILLING_WIRED, "inv/billing/lines.py": LINES})
    assert design["ok"], design["report"]

    money = ticket_of(work, "implement")
    bad = server.kit_submit(str(project.root), money, code=ADD_BAD)
    assert not bad["ok"] and bad["left"] == 2 and any("pytest" in r for r in bad["report"]), bad
    assert "raise NotImplementedError" in project.read("inv.money")             # непринятое в программу не попало
    good = server.kit_submit(str(project.root), money, code=ADD_GOOD)
    assert good["ok"], good["report"]

    leaf = server.kit_next(str(project.root))
    lt = next(t for t in leaf["tickets"] if t["target"] == "inv.billing.lines")
    assert (lt["kind"], lt["model"]) == ("implement", "haiku")
    assert server.kit_submit(str(project.root), lt["ticket"], code=LT_GOOD)["ok"]

    done = server.kit_next(str(project.root))
    assert done["kind"] == "done", done
    state = project.load()
    assert state["phase"] == "done" and all(n["status"] == "done" for n in state["nodes"].values())
    assert '@deal.ensure(lambda a, b, result: result.amount == a.amount + b.amount' in project.read("inv.money")  # карточка цела

    proc = subprocess.run([sys.executable, "-m", "pytest"], cwd=project.root, env=checks.env_for(project.root), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    assert proc.returncode == 0, proc.stdout[-3000:]
    tach = subprocess.run([sys.executable, "-m", "tach", "check"], cwd=project.root, env=checks.env_for(project.root), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=300)
    assert tach.returncode == 0, tach.stdout


def test_splice_takes_only_bodies_and_keeps_the_card():
    sent = "@deal.ensure(lambda a, b, result: True)\ndef add(a: Money, b: Money) -> Money:\n    \"\"\"чужое\"\"\"\n    return Money(1, 'X')\n"
    out, names = cards.splice(MONEY, sent)
    assert names == ["add"] and "return Money(1, 'X')" in out and "result: True" not in out and "чужое" not in out
    assert [c.digest for c in cards.cards(out)] == [c.digest for c in cards.cards(MONEY)]
    with pytest.raises(ValueError, match="подпись"):
        cards.splice(MONEY, "def add(a: Money) -> Money:\n    return a\n")
    with pytest.raises(ValueError, match="кроме функций"):
        cards.splice(MONEY, "import os\n" + ADD_GOOD)
    with pytest.raises(ValueError, match="нет функции"):
        cards.splice(MONEY, "def helper() -> None:\n    pass\n")


def test_example_that_breaks_its_own_condition_is_caught_before_code(tmp_path):
    project = new_project(tmp_path)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    wrong = MONEY.replace("Money(amount=7, currency='USD')", "Money(amount=8, currency='USD')")  # 0 + 7 ≠ 8
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": wrong})
    assert not verdict["ok"] and any("примеры против условий" in r and "PostContractError" in r for r in verdict["report"]), verdict


def test_card_rules_are_enforced_on_designs(tmp_path):
    project = new_project(tmp_path)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    no_examples = MONEY.replace('    >>> add(Money(100, "KZT"), Money(50, "KZT"))\n    Money(amount=150, currency=\'KZT\')\n', "") \
                       .replace('    >>> add(Money(0, "USD"), Money(7, "USD"))\n    Money(amount=7, currency=\'USD\')\n', "")
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": no_examples})
    assert not verdict["ok"] and any("нет примеров doctest" in r for r in verdict["report"])
    no_wiring = ROOT_MODULE.replace("    return total(lines)\n", "    raise NotImplementedError\n")
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/__init__.py": no_wiring})
    assert not verdict["ok"] and any("связка" in r for r in verdict["report"])


def test_designer_cannot_change_the_card_or_reach_outside(tmp_path):
    project = approved(tmp_path)
    design = ticket_of(server.kit_next(str(project.root)), "design")
    changed = BILLING_WIRED.replace("D: 2", "D: 3")
    verdict = server.kit_submit(str(project.root), design, files={"inv/billing/__init__.py": changed, "inv/billing/lines.py": LINES})
    assert not verdict["ok"] and any("карточку узла менять нельзя" in r for r in verdict["report"])
    up = LINES.replace("from inv.types import Line, Money", "from inv import invoice_total  # noqa: F401\nfrom inv.types import Line, Money")
    verdict = server.kit_submit(str(project.root), design, files={"inv/billing/__init__.py": BILLING_WIRED, "inv/billing/lines.py": up})
    assert not verdict["ok"] and any("не может зависеть от inv" in r for r in verdict["report"]), verdict
    verdict = server.kit_submit(str(project.root), design, files={"inv/billing/__init__.py": BILLING_WIRED, "inv/money.py": MONEY})
    assert not verdict["ok"] and any("вне узла" in r for r in verdict["report"])


def test_implementer_cannot_import_or_print_past_the_card(tmp_path):
    project = approved(tmp_path)
    money = next(t["ticket"] for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    sneaky = "def add(a: Money, b: Money) -> Money:\n    import os\n    print(os.getcwd())\n    return Money(a.amount + b.amount, a.currency)\n"
    verdict = server.kit_submit(str(project.root), money, code=sneaky)
    text = "\n".join(verdict["report"])
    assert not verdict["ok"] and "TID251" in text and "T201" in text and "DEL04" in text, text
    cousin = "def add(a: Money, b: Money) -> Money:\n    from inv.billing import total  # noqa: F401\n    return Money(a.amount + b.amount, a.currency)\n"
    verdict = server.kit_submit(str(project.root), money, code=cousin)
    assert not verdict["ok"] and any("[tach]" in r and "inv.billing" in r for r in verdict["report"]), verdict


def test_crosshair_finds_the_input_random_tests_miss(tmp_path):
    """Тело врёт на одном входе из миллиардов: примеры и deal.cases (Hypothesis) его не видят, решатель CrossHair —
    находит и даёт контрпример. Число входа в коде не записано: Hypothesis берёт в перебор литералы кода (10.10 он
    так нашёл `a.amount == 987654321`), а 987654321 здесь выводится только решением a·7 = 6913580247."""
    project = approved(tmp_path)
    money = next(t["ticket"] for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    rare = ("def add(a: Money, b: Money) -> Money:\n    if a.amount * 7 == 6913580247:\n        return Money(0, a.currency)\n"
            "    return Money(a.amount + b.amount, a.currency)\n")
    verdict = server.kit_submit(str(project.root), money, code=rare)
    assert not verdict["ok"] and any(r.startswith("[crosshair]") and "987654321" in r for r in verdict["report"]), verdict


TIGHT_MONEY = MONEY.replace("@deal.pre(lambda a, b: a.currency == b.currency)",
                            "@deal.pre(lambda a, b: a.currency == b.currency and a.amount == b.amount * 1000003 + 17)") \
                   .replace('add(Money(100, "KZT"), Money(50, "KZT"))\n    Money(amount=150,',
                            'add(Money(1000020, "KZT"), Money(1, "KZT"))\n    Money(amount=1000021,') \
                   .replace('add(Money(0, "USD"), Money(7, "USD"))\n    Money(amount=7,', 'add(Money(17, "USD"), Money(0, "USD"))\n    Money(amount=17,')


def test_tight_precondition_leaves_properties_to_crosshair(tmp_path):
    """Условие pre связывает аргументы — Hypothesis не находит ни одного допустимого входа (Unsatisfiable; 11.10 так
    застряли memcore.scrubbing.extension и merging на верных телах). Тест на свойства пропускается с причиной, верное
    тело принято; тело, которое проходит примеры и врёт на b = 2, отвергает CrossHair."""
    assert TIGHT_MONEY.count("1000003") == 1 and "Money(amount=1000021" in TIGHT_MONEY and "Money(amount=17," in TIGHT_MONEY
    project = new_project(tmp_path, seconds=10)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": TIGHT_MONEY})
    assert verdict["ok"], verdict["report"]
    assert server.kit_next(str(project.root))["kind"] == "approve" and server.kit_approve(str(project.root), True)["ok"]
    money = next(t["ticket"] for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    liar = ("def add(a: Money, b: Money) -> Money:\n    if b.amount == 2:\n        return Money(a.amount, a.currency)\n"
            "    return Money(a.amount + b.amount, a.currency)\n")
    verdict = server.kit_submit(str(project.root), money, code=liar)
    assert not verdict["ok"] and any(r.startswith("[crosshair]") for r in verdict["report"]), verdict
    verdict = server.kit_submit(str(project.root), money, code=ADD_GOOD)
    assert verdict["ok"], verdict["report"]


def test_property_runner_ignores_slow_generation():
    """Порог Hypothesis «медленная генерация» (too_slow) меряет время машины, а не тело: 11.10 под шестью
    параллельными сдачами верный merge_spans получил FailedHealthCheck — 7 годных входов из 350 за секунду. Стабильно
    его не вызвать, поэтому проверяется раннер: deal.cases получает настройки kit — без этого порога, без порога
    «много отброшено» и без срока на вызов."""
    import hypothesis
    seen = {}

    def fake_cases(func, **kw):
        seen.update(kw)
        return lambda: None

    ns = {"deal": types.SimpleNamespace(cases=fake_cases), "hypothesis": hypothesis, "pytest": pytest}
    exec(rules.CASES_RUNNER, ns)  # noqa: S102 — тот же текст, что kit пишет в tests/test_rptg_cases.py
    ns["cases"](len)()
    s = seen["settings"]
    assert {hypothesis.HealthCheck.too_slow, hypothesis.HealthCheck.filter_too_much} <= set(s.suppress_health_check)
    assert s.deadline is None and s.database is None and s.max_examples == 50


def test_missing_package_is_environment_not_a_spent_attempt(tmp_path):
    """Карточка импортирует пакет, которого нет в окружении проверок (11.10 — detect-secrets в копии плагина, проектировщик
    потерял две сдачи из трёх): отчёт [env] называет пакет и команду установки, сдача не засчитывается. Пакет, который
    есть, попадает в зависимости pyproject.toml программы."""
    project = new_project(tmp_path)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    absent = MONEY.replace("import deal\n", "import deal\nimport rptg_absent_pkg  # noqa: F401\n", 1)
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": absent})
    text = "\n".join(verdict["report"])
    assert not verdict["ok"] and verdict.get("env") and "[env]" in text and "pip install rptg-absent-pkg" in text, verdict
    assert project.load()["tickets"][arch]["attempts"] == 0
    present = MONEY.replace("import deal\n", "import deal\nimport pathspec  # noqa: F401\n", 1)
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": present})
    assert verdict["ok"], verdict["report"]
    assert '"pathspec"' in (project.root / "pyproject.toml").read_text(encoding="utf-8")


def test_project_venv_is_the_check_interpreter(tmp_path):
    """Своё окружение программы — <папка>/.venv: kit проверяет им, а не окружением сервера. Здесь в нём нет проверок —
    отчёт [env] называет его интерпретатор и недостающий mypy."""
    project = new_project(tmp_path)
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(project.root / ".venv")], check=True, timeout=300,
                   capture_output=True)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    verdict = server.kit_submit(str(project.root), arch, files=ARCHITECTURE)
    text = "\n".join(verdict["report"])
    assert not verdict["ok"] and "[env]" in text and ".venv" in text and "mypy" in text, verdict


def test_roles_see_only_kit_tools():
    """Роли kit — только инструменты kit и чтение: 11.10 исполнитель по ошибке создал карточку задачи в интерфейсе
    (spawn_task) — роли перечисляли запреты, а не разрешения."""
    allowed = {"Read", "Grep", "Glob", "ToolSearch"} | {f"mcp__{s}__kit_{t}" for s in ("plugin_rptg_rptg", "rptg")
                                                         for t in ("brief", "submit", "guide", "status")}
    for f in sorted((ROOT / "agents").glob("rptg-*.md")):
        head = f.read_text(encoding="utf-8").split("---")[1]
        fields = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in head.strip().splitlines())}
        tools = {t.strip() for t in fields["tools"].split(",")}
        assert "disallowedTools" not in fields and tools <= allowed, (f.name, tools - allowed)
        assert {"mcp__plugin_rptg_rptg__kit_brief", "mcp__plugin_rptg_rptg__kit_submit", "mcp__rptg__kit_brief", "mcp__rptg__kit_submit"} <= tools


IO_MONEY = MONEY.replace('"""Деньги одной валюты.\n\nnode: leaf\n"""', '"""Деньги одной валюты и заметка о них.\n\nnode: leaf\neffects: io\n"""') \
                .replace("import deal\n", "from pathlib import Path\n\nimport deal\n", 1) + '''

@deal.ensure(lambda name, result: result == 1)
@deal.has("write")
def save_note(name: str) -> int:
    """Заметка в файл <name>.txt в текущей папке.

    D: 1

    >>> save_note("note")
    1
    """
    raise NotImplementedError
'''
SAVE_GOOD = 'def save_note(name: str) -> int:\n    Path(name + ".txt").write_text("заметка", encoding="utf-8")\n    return 1\n'


def test_effectful_functions_get_no_random_inputs(tmp_path):
    """Функция пишет файл по имени из аргумента. Случайные входы Hypothesis и CrossHair дали бы ей случайные пути —
    мусор где угодно и падения на именах вроде «\\x00»; её проверка — только примеры, и они идут в копии программы:
    в папке проекта файла нет."""
    assert "effects: io" in IO_MONEY and "from pathlib import Path" in IO_MONEY
    project = new_project(tmp_path)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": IO_MONEY})
    assert verdict["ok"], verdict["report"]
    assert server.kit_next(str(project.root))["kind"] == "approve" and server.kit_approve(str(project.root), True)["ok"]
    money = next(t["ticket"] for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    verdict = server.kit_submit(str(project.root), money, code=ADD_GOOD + "\n\n" + SAVE_GOOD)
    assert verdict["ok"], verdict["report"]
    assert not list(project.root.rglob("*.txt"))


HOST_MONEY = MONEY.replace("import deal\n", "import platform\nfrom pathlib import Path\n\nimport deal\n", 1) \
                  .replace("\n\n@deal.pre", "\nHOST = platform.node()  # при импорте — socket.gethostname\n\n\n@deal.pre", 1)
RARE = ("def add(a: Money, b: Money) -> Money:\n    if a.amount * 7 == 6913580247:\n        return Money(0, a.currency)\n"
        "    return Money(a.amount + b.amount, a.currency)\n")


def test_crosshair_sees_past_import_side_effects(tmp_path):
    """Модуль при импорте делает то, что CrossHair считает побочным эффектом (platform.node() → socket.gethostname;
    11.10 numpy под Windows — os.add_dll_directory): модуль импортируется до защиты, и CrossHair всё равно находит
    тело, которое врёт на одном входе; верное принимается. Побочный эффект в самом теле защита по-прежнему ловит:
    запись файла в функции, объявленной чистой, deal lint не видит (Path.write_text), а auditwall CrossHair — видит."""
    assert "HOST = platform.node()" in HOST_MONEY
    project = new_project(tmp_path, seconds=10)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    assert server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": HOST_MONEY})["ok"]
    assert server.kit_next(str(project.root))["kind"] == "approve" and server.kit_approve(str(project.root), True)["ok"]
    money = next(t["ticket"] for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    verdict = server.kit_submit(str(project.root), money, code=RARE)
    assert not verdict["ok"] and any(r.startswith("[crosshair]") and "987654321" in r for r in verdict["report"]), verdict
    noisy = ('def add(a: Money, b: Money) -> Money:\n    Path("note.txt").write_text("x", encoding="utf-8")\n'
             "    return Money(a.amount + b.amount, a.currency)\n")
    verdict = server.kit_submit(str(project.root), money, code=noisy)
    assert not verdict["ok"] and any(r.startswith("[crosshair]") and "SideEffect" in r for r in verdict["report"]), verdict
    verdict = server.kit_submit(str(project.root), money, code=ADD_GOOD)
    assert verdict["ok"], verdict["report"]


def test_architect_submits_from_a_drafts_folder(tmp_path):
    """Главный чат пишет карточки в папку черновиков и сдаёт её путём: kit читает ровно проверенные файлы."""
    drafts = tmp_path / "drafts"
    for rel, text in ARCHITECTURE.items():
        (drafts / rel).parent.mkdir(parents=True, exist_ok=True)
        (drafts / rel).write_text(text, encoding="utf-8")
    project = new_project(tmp_path)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    assert not server.kit_submit(str(project.root), arch, files_from=str(tmp_path / "нет"))["ok"]
    verdict = server.kit_submit(str(project.root), arch, files_from=str(drafts))
    assert verdict["ok"], verdict["report"]
    assert project.read("inv.money") == MONEY


RAISING_MONEY = MONEY.replace("@deal.pre(lambda a, b: a.currency == b.currency)\n",
                              "@deal.pre(lambda a, b: a.currency == b.currency)\n@deal.raises(OverflowError)\n", 1)


def test_card_with_declared_exceptions_passes_design(tmp_path):
    """Карточка с @deal.raises: заглушка `raise NotImplementedError` — не необъявленное исключение (DEL021), а ещё
    не написанное тело; 11.10 так отвергалась карточка convert (FileNotFoundError) у memshell."""
    assert "@deal.raises(OverflowError)" in RAISING_MONEY
    project = new_project(tmp_path)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    verdict = server.kit_submit(str(project.root), arch, files={**ARCHITECTURE, "inv/money.py": RAISING_MONEY})
    assert verdict["ok"], verdict["report"]


def test_check_copies_are_removed(tmp_path, monkeypatch):
    """Каждая сдача проверяется в копии программы во временной папке; после проверок копия удаляется — и у отвергнутой
    сдачи, и у принятой. 11.10 их скопилось 321 (3,7 ГБ), и на диске C кончилось место."""
    import tempfile
    made, real = [], tempfile.mkdtemp

    def spy(*a, **kw):
        d = real(*a, **kw)
        made.append(d)
        return d

    monkeypatch.setattr(tempfile, "mkdtemp", spy)
    project = approved(tmp_path)
    money = next(t["ticket"] for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    assert not server.kit_submit(str(project.root), money, code=ADD_BAD)["ok"]
    assert server.kit_submit(str(project.root), money, code=ADD_GOOD)["ok"]
    assert len(made) >= 3 and not [d for d in made if os.path.exists(d)], [d for d in made if os.path.exists(d)]


def test_ladder_haiku_sonnet_opus_then_owner_revises(tmp_path):
    """Три сдачи одной модели — и билет уходит выше по лестнице; вся лестница не справилась — починка карточек у
    владельца (здесь корень — значит снова архитектор и новое утверждение)."""
    project = approved(tmp_path)
    models = []
    for _ in range(3):
        work = server.kit_next(str(project.root), limit=12)
        t = next(t for t in work["tickets"] if t["target"] == "inv.money")
        models.append(t["model"])
        for _ in range(3):
            server.kit_submit(str(project.root), t["ticket"], code="def add(")
    assert models == ["haiku", "sonnet", "opus"]
    nxt = server.kit_next(str(project.root))
    state = project.load()
    assert nxt["kind"] == "architect" and state["phase"] == "architecture"
    arch = state["tickets"][nxt["tickets"][0]["ticket"]]
    assert "inv.money" in arch["why"] and arch["report"]


def test_new_project_does_not_overwrite_foreign_settings(tmp_path):
    """Папка с чужим pyproject.toml (например, корень PTG-MEM) — не место для проекта kit: файл не трогается."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'чужой'\n", encoding="utf-8")
    out = server.kit_new(str(tmp_path), "inv", "t")
    assert not out["ok"] and "pyproject.toml" in out["error"]
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == "[project]\nname = 'чужой'\n"


def test_connect_writes_project_mcp_config_and_roles(tmp_path):
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
    mcp_file, agents, names = connect.connect(tmp_path)
    data = json.loads(mcp_file.read_text(encoding="utf-8"))
    assert set(data["mcpServers"]) == {"other", "rptg"} and data["mcpServers"]["rptg"]["args"][0].endswith("serve.py")
    assert names == ["rptg-designer.md", "rptg-implementer.md"]
    assert "model: haiku" in (agents / "rptg-implementer.md").read_text(encoding="utf-8")


def test_server_speaks_mcp_over_stdio(tmp_path):
    """Сервер запускается как его запустит Claude Code и отвечает по протоколу MCP."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def talk():
        params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "rptg_kit" / "serve.py")],
                                       env={**checks.env_for(tmp_path), "PYTHONPATH": ""})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                tools = {t.name for t in (await session.list_tools()).tools}
                made = await session.call_tool("kit_new", {"project_dir": str(tmp_path / "p"), "package": "inv", "title": "t"})
                status = await session.call_tool("kit_status", {"project_dir": str(tmp_path / "p")})
                return init, tools, made, status

    init, tools, made, status = asyncio.run(talk())
    assert "kit_next" in (init.instructions or "") and {"kit_new", "kit_next", "kit_brief", "kit_submit", "kit_approve", "kit_status"} <= tools
    assert json.loads(made.content[0].text)["ok"] is True
    assert "фаза architecture" in status.content[0].text


def test_checks_run_through_the_mcp_channel(tmp_path):
    """Сдача с проверками — через тот же канал stdio, что у Claude Code. 10.10.2026 под настоящим Claude Code все
    проверки висели до тайм-аута: инструменты наследовали ввод сервера — канал протокола."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def talk():
        params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "rptg_kit" / "serve.py")],
                                       env={**os.environ, "PYTHONUTF8": "1"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                p = str(tmp_path / "p")
                await session.call_tool("kit_new", {"project_dir": p, "package": "inv", "title": "t"})
                nxt = json.loads((await session.call_tool("kit_next", {"project_dir": p})).content[0].text)
                res = await session.call_tool("kit_submit", {"project_dir": p, "ticket": nxt["tickets"][0]["ticket"], "files": ARCHITECTURE})
                return json.loads(res.content[0].text)

    verdict = asyncio.run(asyncio.wait_for(talk(), 240))
    assert verdict["ok"], verdict


def test_card_parsing_reads_contracts_examples_and_decisions():
    (c,) = cards.cards(MONEY)
    assert (c.name, c.d, c.stub, c.guarantees, len(c.examples)) == ("add", 1, True, 1, 2)
    assert cards.node_kind(MONEY) == "leaf" and cards.node_kind(BILLING_CARD) == "composite"
    assert cards.resolve(cards.imports(BILLING_WIRED, "inv"), {"inv.billing.lines", "inv.money", "inv.types"}) == \
        {"inv.billing.lines", "inv.money", "inv.types"}
    assert textwrap.dedent(cards.replace_bodies(MONEY, {"add": "return a"})).count("return a") == 1
    assert os.sep  # для линтера: os нужен тестам окружения


def test_root_repair_after_approval_keeps_the_built_tree(tmp_path):
    """Починка корня после утверждения — заплатка: собранный лист остаётся собранным, приёмка корня не сбрасывается,
    данные примеров из tests/fixtures/ попадают в программу. 12.10 сборка корня ptgfull не нашла файла заметки, а
    повторная сдача корня целиком сбросила бы 24 собранных листа."""
    from rptg_kit import flow
    project = approved(tmp_path)
    work = server.kit_next(str(project.root))
    assert server.kit_submit(str(project.root), ticket_of(work, "implement"), code=ADD_GOOD)["ok"]
    state = project.load()
    flow.revise(state, "inv", "сборка узла с настоящими детьми не прошла", [])
    project.save(state)
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    verdict = server.kit_submit(str(project.root), arch, files={"inv/__init__.py": ROOT_MODULE, "tests/fixtures/note.md": "заметка\n"})
    assert verdict["ok"], verdict["report"]
    state = project.load()
    assert state["phase"] == "build" and state["approved"]
    assert state["nodes"]["inv.money"]["status"] == "done" and "raise NotImplementedError" not in project.read("inv.money")
    assert state["nodes"]["inv.billing"]["status"] == "card"
    assert (project.root / "tests" / "fixtures" / "note.md").read_text(encoding="utf-8") == "заметка\n"


def test_kit_runs_the_workers_itself(tmp_path, monkeypatch):
    """Прогон волн без главного чата: kit сам запускает исполнителей (`claude -p`, здесь — поддельный) по билетам до
    done; главный чат получает один итог с ценой. 12.10 уведомления исполнителей стоили $6,58 из $11,93 главного чата."""
    from rptg_kit import run
    project = approved(tmp_path)
    monkeypatch.setenv("RPTG_CLAUDE", json.dumps([sys.executable, str(Path(__file__).with_name("fake_worker.py"))]))
    cmd = run.worker_command({"dispatch": "x", "model": "haiku", "agent": "rptg-implementer"})
    assert "--strict-mcp-config" in cmd and "--no-session-persistence" in cmd and '{"disableAllHooks": true}' in cmd
    assert "Вы работаете над одним билетом" in cmd[cmd.index("--append-system-prompt") + 1]
    out = run.run(str(project.root), parallel=4, poll=1)
    assert out["kind"] == "done", out
    assert out["workers"] == 3 and out["accepted"] == 3 and out["cost_usd"] == 0.003
    assert len(list((project.root / ".rptg-kit" / "runs").glob("t*.json"))) == 3


def test_owner_repairs_an_unbuilt_leaf_card(tmp_path):
    """Карточка листа неисполнима (у входа нет предела, занижено D) — владелец меняет её без пересборки родителя:
    открытый билет листа снимается, лестница — с начала, карточка в программе — новая."""
    project = approved(tmp_path)
    work = server.kit_next(str(project.root))
    old = ticket_of(work, "implement")
    fixed = MONEY.replace("D: 1", "D: 2", 1)
    assert fixed != MONEY
    assert not server.kit_recard(str(project.root), files={"inv/__init__.py": ROOT_MODULE})["ok"]   # корень так не чинят
    verdict = server.kit_recard(str(project.root), files={"inv/money.py": fixed})
    assert verdict["ok"], verdict["report"]
    state = project.load()
    assert state["tickets"][old]["status"] == "cancelled" and project.read("inv.money") == fixed
    again = server.kit_next(str(project.root))
    assert any(t["target"] == "inv.money" and t["ticket"] != old for t in again["tickets"])


def built(tmp_path):
    project = approved(tmp_path)
    work = server.kit_next(str(project.root))
    assert server.kit_submit(str(project.root), ticket_of(work, "design"),
                             files={"inv/billing/__init__.py": BILLING_WIRED, "inv/billing/lines.py": LINES})["ok"]
    assert server.kit_submit(str(project.root), ticket_of(work, "implement"), code=ADD_GOOD)["ok"]
    lt = next(t for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.billing.lines")
    assert server.kit_submit(str(project.root), lt["ticket"], code=LT_GOOD)["ok"]
    assert server.kit_next(str(project.root))["kind"] == "done"
    return project


def test_owner_reopens_a_built_node_after_done(tmp_path):
    """Дефект виден уже после done: полный pytest нашёл вход, который случайные проверки сдачи пропустили (13.10
    ptgcore.context.render — оценка inf прошла его фильтр NaN и нарушила условие memshell.render_recall). Владелец
    возвращает узел: составной — проектировщику заплаткой (собранные дети целы), лист — исполнителю; предки
    собираются заново, программа снова done."""
    project = built(tmp_path)
    assert (project.root / "conftest.py").is_file()                                     # примеры — в чистой папке
    report = ["FAILED tests/test_rptg_cases.py::test_inv_billing__total - deal.PreContractError"]
    verdict = server.kit_reopen(str(project.root), "inv.billing", "полный pytest: вход вне условия ребёнка", report)
    assert verdict["ok"], verdict
    state = project.load()
    assert state["phase"] == "build" and state["nodes"]["inv"]["status"] == "designed"
    assert state["nodes"]["inv.billing"]["status"] == "designed" and state["nodes"]["inv.billing.lines"]["status"] == "done"
    work = server.kit_next(str(project.root))
    fix = next(t for t in work["tickets"] if t["target"] == "inv.billing")
    assert fix["kind"] == "revise" and "вход вне условия ребёнка" in server.kit_brief(str(project.root), fix["ticket"])
    assert server.kit_submit(str(project.root), fix["ticket"],
                             files={"inv/billing/__init__.py": BILLING_WIRED, "inv/billing/lines.py": LINES})["ok"]
    assert project.load()["nodes"]["inv.billing.lines"]["status"] == "done"            # неизменённый лист не пересобирается
    assert server.kit_next(str(project.root))["kind"] == "done"

    assert server.kit_reopen(str(project.root), "inv.money", "код неверен на редком входе", report)["ok"]
    assert not server.kit_reopen(str(project.root), "inv.money", "ещё раз", report)["ok"]   # билет уже открыт
    redo = next(t for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.money")
    assert (redo["kind"], redo["model"]) == ("implement", "haiku")
    assert server.kit_submit(str(project.root), redo["ticket"], code=ADD_GOOD)["ok"]
    assert server.kit_next(str(project.root))["kind"] == "done"


COUNT_CARD = '''

@deal.ensure(lambda lines, result: result == len(lines))
@deal.has()
def count(lines: list[Line]) -> int:
    """Число строк.

    D: 1

    >>> count([Line(2, Money(150, "KZT"))])
    1
    """
    raise NotImplementedError
'''


def test_owner_changes_a_built_composite_card_without_rebuilding_its_leaves(tmp_path):
    """Заплатка вглубь: архитектор после done меняет карточки составного ребёнка (13.10 — порог подсказки ptgcore
    менял карточки retrieval и context). Поддерево не сносится: связка функций с прежними карточками остаётся,
    проектировщик получает билет починки под новые карточки, собранный лист не пишется заново."""
    from rptg_kit import cards
    project = built(tmp_path)
    assert server.kit_reopen(str(project.root), "inv", "владелец меняет карточки ребёнка", [])["ok"]
    arch = ticket_of(server.kit_next(str(project.root)), "architect")
    billing = cards.as_card(project.read("inv.billing")) + COUNT_CARD
    verdict = server.kit_submit(str(project.root), arch, files={"inv/__init__.py": ROOT_MODULE, "inv/billing/__init__.py": billing})
    assert verdict["ok"], verdict["report"]
    state = project.load()
    assert state["phase"] == "build" and state["nodes"]["inv.billing"]["status"] == "designed"
    assert state["nodes"]["inv.billing.lines"]["status"] == "done" and "raise NotImplementedError" not in project.read("inv.billing.lines")
    text = project.read("inv.billing")
    assert "acc = add(acc, line_total(line))" in text and text.rstrip().endswith("raise NotImplementedError")
    fix = next(t for t in server.kit_next(str(project.root))["tickets"] if t["target"] == "inv.billing")
    assert fix["kind"] == "revise" and "count" in server.kit_brief(str(project.root), fix["ticket"])
    wired = text.replace("    raise NotImplementedError\n", "    return len(lines)\n")
    assert server.kit_submit(str(project.root), fix["ticket"], files={"inv/billing/__init__.py": wired})["ok"]
    assert project.load()["nodes"]["inv.billing.lines"]["status"] == "done"
    assert server.kit_next(str(project.root))["kind"] == "done"


def test_owner_reopening_the_root_is_not_a_failed_repair(tmp_path):
    """Корень архитектор возвращает себе сам — сколько угодно раз; лимит починок проектировщиков его не трогает (14.10:
    четыре заплатки корня ptgcore подряд заблокировали проект)."""
    project = built(tmp_path)
    for i in range(4):
        assert server.kit_reopen(str(project.root), "inv", f"заплатка {i}", [])["ok"]
        arch = server.kit_next(str(project.root))
        assert arch["kind"] == "architect", arch
        assert server.kit_submit(str(project.root), ticket_of(arch, "architect"), files={"inv/__init__.py": ROOT_MODULE})["ok"]
        assert server.kit_next(str(project.root))["kind"] == "done"
    assert project.load()["blocked"] is None
