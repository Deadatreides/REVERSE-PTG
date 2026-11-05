"""Сервер MCP rptg kit (FastMCP из официального SDK `mcp`): главный чат Claude Code — архитектор и диспетчер,
субагенты (проектировщик — sonnet, исполнитель — haiku, выше по лестнице — sonnet и opus) берут задание и сдают
работу через этот сервер. Каждый вызов держит замок проекта: сдачи параллельных субагентов идут по очереди.
"""
import importlib
import re
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import briefs, flow, rules
from .project import Busy, Project, write_atomic

INSTRUCTIONS = """rptg kit — разработка программы на Python по ТЗ через граф карточек с жёсткими проверками.
Работу принимают готовые проверки (mypy, tach, ruff, deal, Hypothesis, CrossHair, radon), а не модели.

Вы (главный чат) — архитектор и диспетчер. Когда пользователь просит разработать ПО по ТЗ:
1. kit_guide("architect") — прочитайте руководство один раз.
2. kit_new(project_dir, package, title): папка проекта (новая или пустая), имя пакета (латиница, snake_case).
3. kit_next → билет архитектора. Напишите spec.md (шаблон Spec Kit), задайте пользователю не больше 5 уточняющих
   вопросов, напишите корень, types.py и детей корня; сдавайте kit_submit(files=…) до «принято».
4. kit_next → «approve»: покажите пользователю корень (функции, условия, примеры) и kit_status; его ответ — kit_approve.
   Если пользователь заранее сказал «утверждай сам» — утвердите сами.
5. Цикл до «done» — лучше без субагентов: `"{python}" -m rptg_kit.run <папка проекта> --detach`, запуск из папки
   kit `{home}` (это python и папка, на которых работает этот сервер). Прогон уходит вне сеанса (переживает перезапуск приложения), kit сам
   запускает исполнителей (`claude -p` с моделью и ролью билета) волнами до architect / approve / blocked / env / done,
   пишет строку на волну в .rptg-kit/run-progress.log, итог — в .rptg-kit/run.log. Сразу после запуска поставьте
   сторожа — команду, которую печатает --detach, фоновым Bash (run_in_background): он выходит, когда прогон записал
   итог или ход молчит дольше самого долгого исполнителя проекта (по журналу runs/, ~24 мин), и его выход будит главный чат. Kit не опрашивайте; проснулись — kit_status и дело.
   Нужен авторизованный консольный claude. Без него — по-старому:
   kit_next(limit=4) → на каждый билет запустите субагента: Agent(subagent_type = agent из билета —
   rptg-designer или rptg-implementer, при подключении плагином — rptg:rptg-designer / rptg:rptg-implementer, если их
   нет — general-purpose; model = model из билета; prompt = dispatch из билета). Несколько билетов — параллельно в фоне.
   Когда субагенты закончат — снова kit_next. Субагентам не помогайте и их работу не правьте: принимает kit.
   Субагент ответил «сдался: окружение» или kit_next вернул kind «env» — окружению проверок не хватает пакетов: поставьте
   их командой из отчёта (если пакет новый — спросите пользователя о загрузке) и верните того же субагента пересдать
   (SendMessage); сдача из-за окружения не засчитывается. Своё окружение программы — папка .venv в проекте: если она
   есть, kit проверяет ею.
6. «blocked» — покажите пользователю причину и отчёт; его указание — kit_unblock(comment).
7. «done» — запустите `python -m pytest` в папке проекта. Упал тест — kit_reopen(узел, причина, вывод теста) и снова
   шаг 5; прошли — скажите пользователю: пакет в папке проекта; kit_status.

Экономия токенов — обязательные правила. Каждый ход главного чата — чтение всего его контекста, около $0,08 на Opus;
ход исполнителя Haiku стоит около $0,0002. Поэтому:
* Вышестоящая модель получает сигнал только в конце: когда прогон записал итог (done / blocked / approve / architect /
  env) или сторож молчания сработал. Промежуточных сигналов нет.
* Запустили прогон и сторожа — закончите ход. До выхода сторожа ни одного вызова: не опрашивайте kit, не делайте
  kit_status между волнами, не читайте run-progress.log, журналы, runs/ и код исполнителей.
* Без раннера (субагенты): вся волна — в фоне. Уведомления отдельных субагентов не разбирайте и на них не отвечайте;
  берите следующий kit_next, только когда закончилась вся волна.
* Архитектор пишет только карточки: без эталонной реализации и без кода листьев. Работает в свежем чате с малым
  контекстом и не перечитывает файлы, которые kit уже принял.
* Проверки гоняет kit. Модели не запускают pytest, mypy и прочие инструменты сами, кроме итогового pytest на шаге 7.
* Субагенты отвечают одной строкой: «принято» или «сдался: <почему>».
"""

mcp = FastMCP("rptg", instructions=INSTRUCTIONS.replace("{python}", sys.executable)
              .replace("{home}", str(Path(__file__).resolve().parent.parent)))
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


KIT_DIR = Path(__file__).resolve().parent
RELOADABLE = ("cards", "rules", "checks", "briefs", "flow")  # порядок зависимостей; project не перечитывается — замки
LOADED_AT = time.time()


def fresh():
    """Код kit изменён после запуска сервера — перечитать модули на месте. Сервер MCP главного чата живёт весь сеанс:
    17.10 после правки генератора тестов он дважды переписал tests/test_rptg_cases.py старым кодом."""
    global LOADED_AT
    changed = max((p.stat().st_mtime for p in KIT_DIR.glob("*.py")), default=0.0)
    if changed <= LOADED_AT:
        return
    for name in RELOADABLE:
        importlib.reload(sys.modules[f"{__package__}.{name}"])
    LOADED_AT = time.time()


def project_of(project_dir):
    fresh()
    project = Project(project_dir)
    if not project.exists():
        raise ValueError(f"нет проекта rptg kit в {project.root} — сначала kit_new")
    return project


def step(project_dir, action):
    """Действие над состоянием под замком проекта; состояние сохраняется после каждого шага."""
    project = project_of(project_dir)
    try:
        with project.lock():
            state = project.load()
            result = action(project, state)
            project.save(state)
            return result
    except Busy as e:
        return {"ok": False, "error": str(e)}


def release(project_dir, tickets):
    """Для прогона волн (run.py): билеты ушедших исполнителей снова свободны — без 40 минут до перевыдачи."""
    return step(project_dir, lambda project, state: flow.release(state, tickets))


def give_up(project_dir, ticket, reason):
    """Для прогона волн: исполнитель сдался, не исчерпав сдач, — ступень засчитана как неудачная (flow.give_up)."""
    return step(project_dir, lambda project, state: flow.give_up(project, state, ticket, reason))


@mcp.tool()
def kit_guide(topic: str = "architect") -> str:
    """Руководство: architect — роль архитектора (спецификация по Spec Kit, требования EARS, архитектура кодом, правила
    карточек); cards — только правила карточек."""
    return briefs.CARD_RULES if topic == "cards" else briefs.ARCHITECT


@mcp.tool()
def kit_new(project_dir: str, package: str, title: str) -> dict:
    """Новый проект: папка программы с настройками готовых проверок (pyproject.toml — mypy, ruff, pytest; tach.toml)
    и состоянием kit в .rptg-kit/. Папка должна быть новой или без проекта kit."""
    project = Project(project_dir)
    if project.exists():
        return {"ok": False, "error": f"в {project.root} уже есть проект kit — продолжайте kit_next"}
    if not PACKAGE_RE.match(package) or package in ("test", "tests", "types", "deal"):
        return {"ok": False, "error": "имя пакета — латиница в нижнем регистре, цифры и _, не test/tests/types/deal"}
    if (project.root / package).exists():
        return {"ok": False, "error": f"папка {project.root / package} уже есть — выберите другое имя пакета или другую папку"}
    taken = [name for name in ("pyproject.toml", "tach.toml") if (project.root / name).exists()]
    if taken:  # чужие настройки не перезаписываются: проект kit — в своей папке
        return {"ok": False, "error": f"в {project.root} уже есть {', '.join(taken)} — проект kit заводится в отдельной папке"}
    project.root.mkdir(parents=True, exist_ok=True)
    write_atomic(project.root / "pyproject.toml", rules.pyproject(package))
    write_atomic(project.root / "tach.toml", rules.tach_toml({}))
    (project.root / "tests").mkdir(exist_ok=True)
    with project.lock():
        project.save(flow.new_state(package, title))
        project.log("new", package=package, title=title)
    return {"ok": True, "project_dir": str(project.root), "say": "проект создан — kit_next даст билет архитектора"}


@mcp.tool()
def kit_next(project_dir: str, limit: int = 4) -> dict:
    """Что делать дальше: билет архитектора, утверждение корня, билеты субагентам (work), blocked или done.
    Сборка составных узлов идёт здесь же, без модели."""
    return step(project_dir, lambda project, state: flow.next_work(project, state, max(1, min(limit, 12))))


@mcp.tool()
def kit_brief(project_dir: str, ticket: str) -> str:
    """Задание по билету целиком: роль, карточки, соседи, типы, правила, прежние отчёты, как сдавать."""
    project = project_of(project_dir)
    state = project.load()
    t = state["tickets"].get(ticket)
    if t is None:
        return f"нет билета {ticket}"
    if t["status"] != "open":
        return f"билет {ticket} уже закрыт ({t['status']}) — работы по нему нет, ответьте «закрыт»"
    return briefs.brief(project, state, t)


def read_tree(folder):
    """Модули из папки черновиков: {путь от папки через «/»: текст} — все *.py, кроме кэшей, и текстовые данные
    примеров из tests/fixtures/."""
    from pathlib import Path
    base = Path(folder).resolve()
    if not base.is_dir():
        raise ValueError(f"нет папки {base}")
    tree = {str(p.relative_to(base)).replace("\\", "/"): p.read_text(encoding="utf-8") for p in sorted(base.rglob("*.py"))
            if "__pycache__" not in p.parts}
    data = base / "tests" / "fixtures"
    for p in sorted(data.rglob("*")) if data.is_dir() else []:
        if p.is_file():
            try:
                tree[str(p.relative_to(base)).replace("\\", "/")] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # двоичные данные примеров архитектор кладёт сам
    return tree


@mcp.tool()
def kit_submit(project_dir: str, ticket: str, files: dict[str, str] | None = None, code: str | None = None,
               files_from: str | None = None) -> dict:
    """Сдача по билету. Архитектор и проектировщик — files {путь от корня проекта: полный текст модуля}; исполнитель —
    code: блоки def функций модуля (берутся только тела). Главный чат может вместо files дать files_from — папку
    черновиков на диске (её *.py с путями от этой папки): так сдаётся ровно то, что он проверил, без экранирования в
    JSON. Ответ: ok, отчёт проверок, сколько сдач осталось."""
    if files_from:
        try:
            files = {**read_tree(files_from), **(files or {})}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
    return step(project_dir, lambda project, state: flow.submit(project, state, ticket, files=files, code=code))


@mcp.tool()
def kit_approve(project_dir: str, approve: bool, comment: str = "") -> dict:
    """Ответ пользователя на разложение корня: approve=true — утверждено; false — архитектор переделывает (comment —
    что не так)."""
    return step(project_dir, lambda project, state: flow.approve(project, state, approve, comment))


@mcp.tool()
def kit_unblock(project_dir: str, comment: str) -> dict:
    """Указание пользователя по заблокированному узлу: починка с этим указанием (модель — opus)."""
    return step(project_dir, lambda project, state: flow.unblock(project, state, comment))


@mcp.tool()
def kit_recard(project_dir: str, files: dict[str, str] | None = None, files_from: str | None = None, comment: str = "") -> dict:
    """Починка карточек ещё не собранных листьев их владельцем (главный чат — для детей корня), когда отчёт
    субагента показывает, что карточка неисполнима. files — {путь: полный текст модуля} или files_from — папка
    черновиков. Проверка — как у разложения родителя; лист начинает лестницу заново."""
    if files_from:
        try:
            files = {**read_tree(files_from), **(files or {})}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
    return step(project_dir, lambda project, state: flow.recard(project, state, files or {}, comment))


@mcp.tool()
def kit_reopen(project_dir: str, module: str, why: str, report: list[str] | None = None, comment: str = "") -> dict:
    """Собранный узел — снова на починку, когда дефект виден после сборки (полный `pytest` нашёл вход, который
    пропустили проверки сдачи). module — узел с дефектом: составной уходит своему проектировщику (заплатка), лист —
    исполнителю с первой ступени; why и report (вывод теста) — в билет. Предки узла собираются заново."""
    return step(project_dir, lambda project, state: flow.reopen(project, state, module, why, report or (), comment))


@mcp.tool()
def kit_status(project_dir: str) -> str:
    """Дерево узлов с состояниями, билеты, блокировка."""
    project = project_of(project_dir)
    return briefs.status(project, project.load())


def main():
    mcp.run()


if __name__ == "__main__":
    main()
