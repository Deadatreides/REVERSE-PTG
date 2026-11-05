"""Тексты для моделей: руководство архитектора и задания субагентов.

Куски взяты у готовых решений и названы по месту: шаблон спецификации и уточнение — GitHub Spec Kit
(spec-template, /clarify), требования EARS и свойства «для любых …» — AWS Kiro, регламент архитектора (данные,
интерфейсы, поток вызовов) — MetaGPT, иерархия функций с тестами — Parsel, дисциплина исполнителя (ровно задача,
самопроверка до сдачи, свежий субагент на задачу) — obra/superpowers. Приёмку делают проверки kit, а не модели.
"""
from . import cards

CARD_RULES = '''ПРАВИЛА КАРТОЧЕК — закон для всего, что ниже:
1. Узел — модуль Python. Лист — <имя>.py, составной — пакет <имя>/__init__.py. В описании модуля — назначение и
   строка «node: leaf» или «node: composite».
2. Импорты — только вверху модуля и только абсолютные (from <пакет>.x import y). Они объявляют, чем узел может
   пользоваться: типами (<пакет>.types), своими детьми, братьями и тем, что может родитель. Исполнитель импортов не
   добавит — их держит tach.
3. Каждая функция — карточка:
       import deal

       @deal.pre(lambda <аргументы>: <условие>)             # 0 и больше: что обещает вызывающий
       @deal.ensure(lambda <аргументы>, result: <условие>)   # у листа хотя бы одно: что обещает функция
       @deal.has()                                           # побочные эффекты; () — чистая функция
       def имя(арг: Тип) -> Тип:
           """Что делает.

           D: <число решений: ветвления + циклы + досрочные выходы; 1 — прямой код>

           >>> имя(<готовые значения>)
           <точный repr результата>
           """
           raise NotImplementedError
4. Примеры — 2–5 на функцию: один вызов этой функции с готовыми значениями; ожидание — точный repr (класс данных
   печатается как Money(amount=300, currency='KZT')). Примеры покрывают края из спецификации. kit сверяет каждый
   пример с условиями карточки ещё до кода.
5. Условия — выражения Python от аргументов и result, без исключений на допустимых входах.
6. Листья маленькие: D ≤ 8 на функцию (сложность кода kit ограничит 1,5·D + 5).
7. Функции составного узла пишет его проектировщик сразу — связка из вызовов детей.
8. Побочные эффекты (файлы, сеть, печать) — только там, где их требует ТЗ: строка «effects: io» в описании модуля и
   маркеры в @deal.has("io", "stdout", …). Функции с маркерами случайных входов и решателя не получают — их проверка
   только примеры, поэтому эффект выносите в тонкую функцию, а решения — в чистые. Примеры таких функций идут в
   одноразовой копии программы: пути в примерах — относительные (в текущей папке), без внешних служб.'''

ARCHITECT = f'''РОЛЬ: архитектор rptg kit — главный чат. Работу принимают проверки kit, а не модели.

Шаг 1. Спецификация — шаблон GitHub Spec Kit (spec-template), сокращённый. Файл <проект>/spec.md на языке пользователя:
  • пользовательские истории с приоритетом (P1, P2 …), каждая проверяется отдельно; у каждой — сценарии приёмки
    «Дано … Когда … Тогда …»;
  • требования ФТ-001 … в форме EARS (Kiro): «КОГДА <событие> СИСТЕМА ДОЛЖНА <отклик>»; правила для всех входов —
    свойства: «Для любых <входы> … СИСТЕМА ДОЛЖНА …»;
  • сущности (данные), крайние случаи, допущения, измеримые критерии успеха;
  • пробелы — [НУЖНО УТОЧНИТЬ: вопрос]. Пользователю — не больше 5 таких вопросов (Spec Kit /clarify), только те, что
    меняют поведение программы; остальное — разумное умолчание в «Допущениях».
Шаг 2. Архитектура — регламент архитектора MetaGPT (структуры данных, интерфейсы, поток вызовов), сразу кодом:
  • <пакет>/types.py — замороженные классы данных (@dataclass(frozen=True)) для всех сущностей, поля с типами;
  • <пакет>/__init__.py — корень: публичные функции программы (карточки) и их связка;
  • дети корня — по одной ответственности на узел, 2–7 штук.
  Сценарии приёмки — примеры doctest корневых функций (это приёмка программы, после утверждения их не меняют);
  свойства «для любых …» — @deal.ensure.
Шаг 3. Сдача: kit_submit(project_dir, ticket, files={{путь: полный текст}}) — корень, types.py и модули детей
  корня. Читайте отчёт, правьте, сдавайте снова, пока не «принято».
Шаг 4. Утверждение: покажите пользователю корень и дерево (kit_status); его ответ — kit_approve.
Шаг 5. Обход: kit_next → субагенты по билетам → kit_next … до «done».

{CARD_RULES}'''


def card_text(source):
    """Карточки модуля без тел — для соседей: декораторы, подпись, описание."""
    out = []
    for c in cards.cards(source):
        out += [*(f"@{d}" for d in c.decorators), c.signature + ":", '    """' + c.doc.replace("\n", "\n    ") + '"""', ""]
    return "\n".join(out).rstrip()


def neighbours(project, state, module):
    from .project import parent_of
    deps = cards.resolve(cards.imports(project.read(module), state["package"]), set(state["nodes"]))
    parent = parent_of(module)
    visible = set(deps)
    if parent:
        visible |= {m for m, n in state["nodes"].items() if n.get("parent") == parent and m != module}
        visible |= cards.resolve(cards.imports(project.read(parent), state["package"]), set(state["nodes"])) - {module}
    visible -= {f"{state['package']}.types", module, parent}
    parts = []
    for m in sorted(v for v in visible if v and v in state["nodes"]):
        parts.append(f"# {m}\n{card_text(project.read(m))}")
    return "\n\n".join(parts) or "(нет)"


def types_text(project, state):
    path = project.root / state["package"] / "types.py"
    return path.read_text(encoding="utf-8") if path.exists() else "(типов ещё нет)"


def history(t):
    parts = []
    if t.get("note"):
        parts.append(f"УКАЗАНИЕ ПОЛЬЗОВАТЕЛЯ: {t['note']}")
    if t.get("why"):
        parts.append(f"ПОЧИНКА — причина: {t['why']}\nОтчёт проверок:\n" + "\n".join(t.get("report", [])))
    for h in t.get("history", []):
        parts.append(f"ПРЕЖНЯЯ ПОПЫТКА ({h['model']}) не прошла:\n" + "\n".join(h["report"]))
    return "\n\n".join(parts)


def brief(project, state, t):
    tid, root, module, k = t["id"], project.root, t["target"], state["limits"]["attempts"]
    if t["kind"] == "architect":
        own = "\n\nТЕКУЩИЙ КОРЕНЬ:\n" + project.read(module) if (project.root / module / "__init__.py").exists() else ""
        return (f"{ARCHITECT}\n\nБИЛЕТ: {tid}; пакет {state['package']}; проект {root}; задача: {state['title']}.\n"
                f"Сдача: kit_submit(project_dir=\"{root}\", ticket=\"{tid}\", files={{...}}).{own}\n\n{history(t)}").rstrip()
    if t["kind"] in ("design", "revise"):
        pkg_dir = "/".join(module.split("."))
        return f'''РОЛЬ: проектировщик rptg kit. Задача — разложить узел {module} на детей-карточки и написать его связку.

Карточка узла (не менять декораторы, подписи и описания — только тела функций):
{project.read(module)}

Что видно узлу кроме своих детей (карточки соседей):
{neighbours(project, state, module)}

Типы ({state['package']}/types.py; правит только архитектор):
{types_text(project, state)}

Сделайте:
1. Разбейте узел на 2–7 детей, по одной ответственности; каждый ребёнок проверяется своими примерами (Parsel:
   иерархия функций с тестами).
2. Каждого ребёнка — карточкой-модулем по правилам ниже: лист — {pkg_dir}/<имя>.py, составной —
   {pkg_dir}/<имя>/__init__.py.
3. Тела функций узла замените связкой — вызовами детей.
4. До сдачи проверьте сами: каждый пример ребёнка согласован с его условиями; примеры узла получаются из примеров детей.

Сдача: kit_submit(project_dir="{root}", ticket="{tid}", files={{"{pkg_dir}/__init__.py": <полный текст>, "<путь ребёнка>": <полный текст>, …}}).
kit прогонит mypy, tach, ruff, deal lint и сверит примеры с условиями. Чините по отчёту и сдавайте снова (до {k} сдач).
В конце — одна строка: «принято» или «сдался: <почему>».

{CARD_RULES}

{history(t)}'''.rstrip()
    return f'''РОЛЬ: исполнитель rptg kit. Напишите тела функций модуля {module} — ровно по карточкам.

Модуль (карточки):
{project.read(module)}

Что модуль может вызывать (карточки соседей):
{neighbours(project, state, module)}

Типы:
{types_text(project, state)}

Правила (дисциплина исполнителя superpowers: ровно задача, ничего сверх):
• Только тела функций: декораторы, подписи и описания kit оставит из карточки — присланные он не берёт.
• Новых импортов нет: только то, что модуль уже импортирует, и встроенные функции Python. Помощники — вложенными
  функциями внутри тела.
• До сдачи проверьте сами: каждый пример даёт ровно свою строку; каждое ensure выполняется на всех входах, которые
  допускает pre (пустые списки, ноль, отрицательные, границы).

Сдача: kit_submit(project_dir="{root}", ticket="{tid}", code="<блоки def всех функций модуля>").
kit прогонит mypy, tach, ruff, deal lint, radon, doctest, deal.cases (Hypothesis: сотни входов из условий) и
CrossHair (решатель ищет вход-нарушитель). Чините по отчёту и сдавайте снова (до {k} сдач). В конце — одна строка:
«принято» или «сдался: <почему>».

{history(t)}'''.rstrip()


def status(project, state):
    lines = [f"{state['title']} — пакет {state['package']}, фаза {state['phase']}"]

    def walk(module, depth):
        node = state["nodes"].get(module)
        if not node:
            return
        funcs = len([k for k in state["cards"] if k.split(":")[0] == module])
        lines.append(f"{'  ' * depth}{module} [{node['status']}] {node['kind']}, функций {funcs}"
                     + (f", ступень {node['rung']}" if node.get("rung") else "") + (f", починок {node['revisions']}" if node.get("revisions") else ""))
        for c in sorted(m for m, n in state["nodes"].items() if n.get("parent") == module):
            walk(c, depth + 1)

    walk(state["package"], 0)
    tickets = list(state["tickets"].values())
    lines.append("билеты: " + ", ".join(f"{s} {sum(1 for t in tickets if t['status'] == s)}" for s in ("open", "done", "failed")))
    if state["blocked"]:
        lines.append(f"ЗАБЛОКИРОВАНО: {state['blocked']['reason']}")
    return "\n".join(lines)
