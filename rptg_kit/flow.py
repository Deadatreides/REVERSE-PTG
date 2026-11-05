"""Обход карточек: билеты задач, лестница моделей, починки, утверждение корня.

Порядок работ — от корня вниз (разложения), потом снизу вверх (код листьев, затем сборка составных): лист
пишется, когда готово всё, что он импортирует. Модель задачи — ступень лестницы роли (по умолчанию: проект —
sonnet → opus, код — haiku → sonnet → opus); билет — до `attempts` сдач одной моделью, она чинит по отчёту
проверок сама. Исчерпанная лестница кода — починка карточек у владельца (проектировщика родителя), исчерпанные
починки — вопрос пользователю. Разложение корня утверждает пользователь, его новая версия — снова.
"""
import ast
from graphlib import TopologicalSorter

from . import briefs, cards, checks, rules
from .project import module_of, now, parent_of

LADDERS = {"design": ["sonnet", "opus"], "implement": ["haiku", "sonnet", "opus"]}
LIMITS = {"attempts": 3, "revisions": 2, "crosshair_seconds": 5, "architect_attempts": 12, "reissue_minutes": 40}
AGENTS = {"architect": "main", "design": "rptg-designer", "revise": "rptg-designer", "implement": "rptg-implementer"}
FIXTURES = "tests/fixtures/"  # данные примеров архитектора: файлы, на которые ссылаются примеры корня
ENV_FREE = 2  # сдач на билет, которые не засчитываются из-за нехватки окружения проверок (дальше — как обычно)


def new_state(package, title):
    return {"version": 1, "package": package, "title": title, "created": now(), "phase": "architecture", "nodes": {}, "cards": {},
            "tickets": {}, "counter": 0, "approved": None, "blocked": None, "ladders": LADDERS, "limits": LIMITS}


def issue(state, kind, target, model, **extra):
    state["counter"] += 1
    tid = f"t{state['counter']:04d}"
    state["tickets"][tid] = {"id": tid, "kind": kind, "target": target, "model": model, "agent": AGENTS[kind], "attempts": 0,
                             "status": "open", "issued_at": now(), "handed_at": None, **extra}
    return tid


def open_ticket(state, target, kinds=None):
    return next((t for t in state["tickets"].values() if t["status"] == "open" and t["target"] == target
                 and (kinds is None or t["kind"] in kinds)), None)


def children(state, node):
    return sorted(m for m, n in state["nodes"].items() if n.get("parent") == node and n["kind"] != "types")


def subtree(state, node):
    out = []
    for c in children(state, node):
        out += [c, *subtree(state, c)]
    return out


def view(state, project, t):
    """Билет для главного чата: кого звать, какой моделью и что сказать субагенту."""
    return {"ticket": t["id"], "kind": t["kind"], "target": t["target"], "role": t["agent"], "model": t["model"],
            "agent": t["agent"], "attempt_limit": state["limits"]["attempts"],
            "dispatch": (f"rptg kit, билет {t['id']} в проекте {project.root}. Вызови kit_brief(project_dir=\"{project.root}\", "
                         f"ticket=\"{t['id']}\") и сделай ровно то, что там сказано; сдавай только через kit_submit. Файлы не правь, "
                         "команды не запускай. В конце — одна строка: «принято» или «сдался: <почему>».")}


# --- что делать дальше ---------------------------------------------------------------------------------------
def next_work(project, state, limit=4):
    """Следующие задачи. Сборка составных узлов идёт здесь же, без модели."""
    if state["phase"] == "done":
        return {"kind": "done", "summary": briefs.status(project, state)}
    if state["blocked"]:
        return {"kind": "blocked", **state["blocked"]}
    if state["phase"] == "architecture":
        t = open_ticket(state, state["package"], {"architect"}) or state["tickets"][issue(state, "architect", state["package"], "opus")]
        t["handed_at"] = now()
        return {"kind": "architect", "tickets": [view(state, project, t)],
                "say": "Архитектуру пишет главный чат сам: kit_guide('architect'), затем kit_brief и kit_submit с этим билетом."}
    if state["phase"] == "approval":
        return {"kind": "approve", "summary": briefs.status(project, state), "root": project.read(state["package"]),
                "say": "Покажите пользователю корень (функции, условия, примеры) и дерево узлов; его ответ — kit_approve."}
    env = integrate_ready(project, state)
    if env:
        return {"kind": "env", "report": env,
                "say": "Сборке не хватает окружения проверок: поставьте пакеты командой из отчёта и снова kit_next."}
    if state["phase"] == "done":
        return {"kind": "done", "summary": briefs.status(project, state)}
    if state["blocked"]:
        return {"kind": "blocked", **state["blocked"]}
    for module, node in sorted(state["nodes"].items()):
        if node["status"] != "card" or open_ticket(state, module):
            continue
        if node["kind"] == "composite":
            issue(state, "design", module, ladder(state, "design", node["rung"]))
        elif node["kind"] == "leaf" and ready(project, state, module):
            issue(state, "implement", module, ladder(state, "implement", node["rung"]))
    stale = minutes(state["limits"]["reissue_minutes"])
    fresh = [t for t in state["tickets"].values() if t["status"] == "open" and t["kind"] != "architect"
             and (t["handed_at"] is None or t["handed_at"] < stale)]
    order = {"revise": 0, "design": 1, "implement": 2}
    fresh.sort(key=lambda t: (order[t["kind"]], t["id"]))
    for t in fresh[:limit]:
        t["handed_at"] = now()
    busy = sum(1 for t in state["tickets"].values() if t["status"] == "open") - len(fresh[:limit])
    if not fresh and not busy:
        return {"kind": "blocked", "reason": "нечего делать, а программа не собрана — ошибка обхода", "summary": briefs.status(project, state)}
    return {"kind": "work", "tickets": [view(state, project, t) for t in fresh[:limit]], "in_progress": busy,
            "say": "Запустите по субагенту на билет (subagent_type = agent, model = model, prompt = dispatch); можно параллельно. "
                   "Когда они закончат — снова kit_next." if fresh[:limit] else "Все задачи розданы — дождитесь субагентов и снова kit_next."}


def minutes(n):
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=n)).isoformat(timespec="seconds")


def ladder(state, role, rung):
    steps = state["ladders"][role]
    return steps[min(rung, len(steps) - 1)]


def ready(project, state, module):
    """Лист готов к коду, когда готово всё, что он импортирует (кроме типов)."""
    deps = cards.resolve(cards.imports(project.read(module), state["package"]), set(state["nodes"]))
    return all(state["nodes"].get(d, {}).get("status") == "done" for d in deps)


def integrate_ready(project, state):
    """Составные узлы, все дети которых готовы, — сборка: их примеры и свойства с настоящими детьми."""
    order = TopologicalSorter({m: set(children(state, m)) for m, n in state["nodes"].items() if n["kind"] == "composite"})
    for module in order.static_order():
        node = state["nodes"].get(module)
        if not node or node["kind"] != "composite" or node["status"] != "designed" or open_ticket(state, module):
            continue
        if not all(state["nodes"][c]["status"] == "done" for c in children(state, module)) or not ready(project, state, module):
            continue  # сборке нужны готовые дети и всё, что узел импортирует (братья, наследованное от родителя)
        stage = project.stage()
        rel = str(project.path_of(module)).replace("\\", "/")
        names = [c.name for c in cards.cards(project.read(module))]
        try:
            found = checks.integrate(stage, state["package"], rel, names, state["limits"]["crosshair_seconds"])
        finally:
            project.discard(stage)
        project.log("integrate", node=module, ok=not found, report=[str(f) for f in found])
        if found and all(f.tool == "env" for f in found):
            return [str(f) for f in found]  # окружению чего-то не хватает: сборка ждёт, узел не чинится
        if found:
            revise(state, module, "сборка узла с настоящими детьми не прошла", found)
        else:
            node["status"] = "done"
            if module == state["package"]:
                state["phase"] = "done"
                write_cases(project, state)
    return []


def write_cases(project, state):
    funcs = [f"{m}:{c.name}" for m, n in state["nodes"].items() if n["kind"] in ("leaf", "composite") for c in cards.cards(project.read(m))
             if not c.effects]  # функциям с побочными эффектами случайных входов не дают (checks.pure)
    from .project import write_atomic
    write_atomic(project.root / "tests" / "test_rptg_cases.py", rules.cases_test(state["package"], funcs))
    write_atomic(project.root / "conftest.py", rules.CONFTEST)


def revise(state, module, why, found, comment=""):
    """Починка карточек узла его проектировщиком; лимит починок — вопрос пользователю."""
    node = state["nodes"][module]
    node["revisions"] = node.get("revisions", 0) + 1
    report = [str(f) for f in found]
    if node["revisions"] > state["limits"]["revisions"]:
        state["blocked"] = {"reason": f"{module}: {why}; починок было {node['revisions'] - 1} — нужен ваш ответ (kit_unblock)",
                            "node": module, "report": report}
        return None
    kind = "architect" if module == state["package"] else "revise"
    model = "opus" if kind == "architect" else ladder(state, "design", node["revisions"] - 1)
    if kind == "architect":
        state["phase"] = "architecture"
    return issue(state, kind, module, model, why=why, report=report, note=comment)


# --- сдача ---------------------------------------------------------------------------------------------------
def submit(project, state, tid, files=None, code=None):
    t = state["tickets"].get(tid)
    if t is None:
        return {"ok": False, "report": [f"нет билета {tid}"]}
    if t["status"] != "open":
        return {"ok": t["status"] == "done", "report": [f"билет {tid} уже закрыт: {t['status']}"], "final": True}
    t["attempts"] += 1
    stages = []  # копии программы этой сдачи: удаляются после проверок при любом исходе (project.discard)
    try:
        if t["kind"] == "implement":
            found, accepted = submit_code(project, state, t, code or "", stages)
        else:
            found, accepted = submit_design(project, state, t, files or {}, stages)
    finally:
        for s in stages:
            project.discard(s)
    report = [str(f) for f in found]
    project.log("submit", ticket=tid, kind=t["kind"], target=t["target"], model=t["model"], attempt=t["attempts"], ok=accepted, report=report)
    if accepted:
        t["status"] = "done"
        return {"ok": True, "report": [], "final": True, "say": "принято"}
    limit = state["limits"]["architect_attempts" if t["kind"] == "architect" else "attempts"]
    if found and all(f.tool == "env" for f in found) and t.get("env_free", 0) < ENV_FREE:
        t["attempts"] -= 1  # нехватка окружения — не ошибка сдачи
        t["env_free"] = t.get("env_free", 0) + 1
        return {"ok": False, "report": report, "final": True, "env": True, "left": limit - t["attempts"],
                "say": "окружению проверок чего-то не хватает — сдача не засчитана; если не опечатка в импорте, ответьте "
                       "«сдался: окружение» и приложите отчёт"}
    if t["attempts"] < limit:
        return {"ok": False, "report": report, "final": False, "left": limit - t["attempts"]}
    t["status"] = "failed"
    escalate(state, t, found)
    return {"ok": False, "report": report, "final": True, "say": "попытки этой модели кончились — задача уйдёт выше по лестнице"}


def escalate(state, t, found):
    module = t["target"]
    node = state["nodes"].get(module, {})
    history = [*t.get("history", []), {"model": t["model"], "report": [str(f) for f in found][:6]}]
    if t["kind"] in ("implement", "design"):
        role = t["kind"]
        node["rung"] = node.get("rung", 0) + 1
        if node["rung"] < len(state["ladders"][role]):
            issue(state, role, module, ladder(state, role, node["rung"]), history=history)
            return
        node["rung"] = 0
        parent = parent_of(module)
        revise(state, parent, f"{module}: ни одна модель лестницы не прошла проверки — карточка, видимо, неисполнима", found)
    elif t["kind"] == "revise":
        revise(state, module, t.get("why", "починка не прошла проверки"), found)
    else:
        state["blocked"] = {"reason": "архитектура не прошла проверки за отведённые сдачи — нужен ваш ответ", "node": module,
                            "report": [str(f) for f in found][:8]}


def allowed_paths(project, state, module, kind):
    """Файлы, которые может прислать проектировщик узла: свой модуль-пакет и прямые дети; у корня — ещё types.py."""
    pkg_dir = "/".join(module.split("."))
    own = f"{pkg_dir}/__init__.py"
    return own, (lambda rel: rel == own or (rel.startswith(pkg_dir + "/") and (rel.count("/") == pkg_dir.count("/") + 1
                                              or (rel.count("/") == pkg_dir.count("/") + 2 and rel.endswith("/__init__.py")))))


def submit_design(project, state, t, files, stages):
    from .checks import Finding
    module, package = t["target"], state["package"]
    own, inside = allowed_paths(project, state, module, t["kind"])
    files = {k.replace("\\", "/").lstrip("./"): v for k, v in files.items()}
    # данные примеров (заметки, страницы) — только у архитектора, в tests/fixtures/; это не узлы
    fixtures = {rel: text for rel, text in files.items() if module == package and rel.startswith(FIXTURES)}
    files = {rel: text for rel, text in files.items() if rel not in fixtures}
    bad = [rel for rel in files if not inside(rel) or not rel.endswith(".py")]
    if bad:
        return [Finding("scope", f"файлы вне узла {module}: {', '.join(bad)} — можно {own} и прямых детей")], False
    if module != package and f"{package}/types.py" in files:
        return [Finding("scope", "типы правит только архитектор (корень)")], False
    old = project.path_of(module)
    if module != package and str(old).replace("\\", "/") != own:
        return [Finding("scope", f"{module} — составной узел, но его карточка — модуль {old}; так быть не должно")], False
    # Починка после утверждения — заплатка: меняются только присланные модули; неприсланные дети и неизменённые
    # (текст тот же) сохраняют состояние и поддерево. Иначе одна правка корня снесла бы всё собранное дерево.
    patch = bool(state.get("approved")) and module in state["nodes"] and state["nodes"][module].get("status") == "designed"
    stage = project.stage()
    stages.append(stage)
    for rel, text in {**files, **fixtures}.items():
        (stage / rel).parent.mkdir(parents=True, exist_ok=True)
        (stage / rel).write_text(text, encoding="utf-8", newline="\n")
    if not (stage / own).exists():
        return [Finding("scope", f"нет модуля узла {own}")], False
    # неизменённый ребёнок — тот же текст или та же карточка у собранного (тела не в счёт: проектировщик шлёт заглушки)
    same = {rel for rel in files if rel != own and patch and (project.root / rel).is_file()
            and same_card((project.root / rel).read_text(encoding="utf-8"), files[rel])}
    changed = {module_of(rel): rel for rel in files if rel != own and rel not in same}
    # заплатка вглубь: у разложенного составного ребёнка с новыми карточками поддерево не сносится — его проектировщик
    # получает билет починки под новые карточки, собранные листья под ним остаются (13.10: правка порога подсказки
    # ptgcore меняла карточки retrieval и context — без этого их листья писались бы заново)
    reworked = {c for c, rel in changed.items() if patch and state["nodes"].get(c, {}).get("kind") == "composite"
                and state["nodes"][c].get("status") in ("designed", "done") and cards.node_kind(files[rel]) == "composite"}
    # прежнее поддерево узла снимается в копии: новый набор детей — целиком из сдачи (при заплатке — только у изменённых)
    dropped = [m for m in subtree(state, module)
               if not patch or any(m == c or m.startswith(c + ".") for c in set(changed) - reworked)]
    retired = []
    for old_child in dropped:
        rel = str(project.path_of(old_child)).replace("\\", "/")
        if rel not in files:
            retired.append(rel)
            (stage / rel).unlink(missing_ok=True)
    child_rels = sorted(rel for rel in files if rel != own and rel not in same)
    frozen = None if module == package else {name: digest for key, digest in state["cards"].items()
                                              for m, _, name in [key.partition(":")] if m == module}
    pkg_files = {str(p.relative_to(stage)).replace("\\", "/"): p.read_text(encoding="utf-8") for p in (stage / package).rglob("*.py")}
    imported = checks.third_party(pkg_files, package)
    deps = [checks.dist_of(n) for n in imported]
    (stage / "pyproject.toml").write_text(rules.pyproject(package, rules.io_modules(pkg_files), deps, imported),
                                          encoding="utf-8", newline="\n")
    found = checks.design(stage, package, module, own, child_rels, frozen, first_root=module == package)
    if found:
        return found, False
    for child in reworked:  # у переделываемого составного связка функций с прежними карточками остаётся
        rel = changed[child]
        old = {k.partition(":")[2]: v for k, v in state["cards"].items() if k.split(":")[0] == child}
        keep = {c.name for c in cards.cards(files[rel]) if old.get(c.name) == c.digest}
        (stage / rel).write_text(cards.keep_bodies(files[rel], (project.root / rel).read_text(encoding="utf-8"), keep),
                                 encoding="utf-8", newline="\n")
    project.retire([r for r in retired if r not in files])
    project.apply(stage, [own, *child_rels, *sorted(fixtures), "tach.toml", "pyproject.toml"])
    before = {k: v for k, v in state["cards"].items() if k.split(":")[0] == module}
    for gone in dropped:
        state["nodes"].pop(gone, None)
        for key in [k for k in state["cards"] if k.split(":")[0] == gone]:
            state["cards"].pop(key)
    for rel in child_rels:
        child = module_of(rel)
        text = files[rel]
        kind = "types" if child == f"{package}.types" else cards.node_kind(text)
        old_cards = {k.partition(":")[2]: state["cards"].pop(k) for k in [k for k in state["cards"] if k.split(":")[0] == child]}
        new_cards = {c.name: c.digest for c in cards.cards(text)}
        if child in reworked:
            for t in state["tickets"].values():
                if t["target"] == child and t["status"] == "open":
                    t["status"] = "cancelled"
            state["nodes"][child]["status"] = "designed"
            moved = sorted(n for n in new_cards.keys() | old_cards.keys() if new_cards.get(n) != old_cards.get(n))
            issue(state, "revise", child, ladder(state, "design", 0),
                  why="владелец изменил карточки узла — допишите связку под них; детей, чьи карточки не меняются, не трогайте",
                  report=[f"изменены или новые: {', '.join(n for n in moved if n in new_cards)}"] +
                         ([f"сняты: {', '.join(n for n in moved if n not in new_cards)}"] if any(n not in new_cards for n in moved) else []))
        else:
            state["nodes"][child] = {"kind": kind, "parent": module, "status": "done" if kind == "types" else "card", "rung": 0, "revisions": 0}
        for name, digest in new_cards.items():
            state["cards"][f"{child}:{name}"] = digest
    node = state["nodes"].setdefault(module, {"kind": "composite", "parent": parent_of(module), "rung": 0, "revisions": 0})
    node["status"] = "designed"
    if module == package:
        for c in cards.cards(files.get(own, project.read(module))):
            state["cards"][f"{module}:{c.name}"] = c.digest
        after = {k: v for k, v in state["cards"].items() if k.split(":")[0] == module}
        if patch and after == before:
            state["phase"] = "build"  # приёмка корня (его карточки) не менялась — утверждение в силе
        else:
            state["phase"] = "approval"
            state["approved"] = None
    return [], True


def submit_code(project, state, t, code, stages):
    from .checks import Finding
    module, package = t["target"], state["package"]
    rel = str(project.path_of(module)).replace("\\", "/")
    base = t.get("staged") or project.read(module)
    try:
        text, _ = cards.splice(base, code)
    except ValueError as e:
        return [Finding("card", str(e))], False
    t["staged"] = text  # следующая сдача того же билета дописывает к этой
    left = [c.name for c in cards.cards(text) if c.stub]
    if left:
        return [Finding("card", f"ещё не написаны: {', '.join(left)} — пришлите их (можно вместе с уже присланными)")], False
    stage = project.stage()
    stages.append(stage)
    (stage / rel).write_text(text, encoding="utf-8", newline="\n")
    found = checks.implement(stage, package, rel, [c.name for c in cards.cards(text)], state["limits"]["crosshair_seconds"])
    if found:
        return found, False
    project.apply(stage, [rel])
    state["nodes"][module]["status"] = "done"
    return [], True


def approve(project, state, ok, comment=""):
    if state["phase"] != "approval":
        return {"ok": False, "say": f"сейчас нечего утверждать (фаза {state['phase']})"}
    if ok:
        state["phase"] = "build"
        state["approved"] = {"at": now(), "cards": {k: v for k, v in state["cards"].items() if k.split(":")[0] == state["package"]}}
        project.log("approve", ok=True)
        return {"ok": True, "say": "утверждено — дальше kit_next"}
    state["phase"] = "architecture"
    issue(state, "architect", state["package"], "opus", note=comment, why="пользователь не утвердил разложение корня")
    project.log("approve", ok=False, comment=comment)
    return {"ok": True, "say": "отклонено — архитектор переделывает (kit_next даст билет)"}


def unblock(project, state, comment):
    b = state["blocked"]
    if not b:
        return {"ok": False, "say": "ничего не заблокировано"}
    module = b.get("node") or state["package"]
    state["blocked"] = None
    state["nodes"].get(module, {})["revisions"] = 0
    kind = "architect" if module == state["package"] else "revise"
    if kind == "architect":
        state["phase"] = "architecture"
    issue(state, kind, module, "opus", why=b["reason"], report=b.get("report", []), note=comment)
    project.log("unblock", node=module, comment=comment)
    return {"ok": True, "say": f"{module}: починка с вашим указанием — kit_next даст билет"}


def release(state, tickets):
    """Открытые билеты снова свободны к выдаче (исполнитель ушёл, не исчерпав сдач)."""
    for tid in tickets:
        t = state["tickets"].get(tid)
        if t and t["status"] == "open":
            t["handed_at"] = None
    return {"ok": True}


def give_up(project, state, tid, reason):
    """Исполнитель ответил «сдался», а билет ещё открыт (сдач не было или они не кончились): ступень засчитывается
    неудачной и задача идёт выше по лестнице, с вершины — проектировщику родителя. Без этого карточка, которой не
    хватает импорта, крутилась на одной ступени: каждый исполнитель сдавался, не сдав, попытки не тратились, и прогон
    выходил с «work» (17.10, graphlm: gxs.cleanup, gxs.indexdb, vocab.bpe, gxs.pagefile). «Сдался: окружение» —
    не неудача ступени: окружение чинит главный чат."""
    from .checks import Finding
    t = state["tickets"].get(tid)
    if t is None or t["status"] != "open" or t["kind"] not in ("implement", "design", "revise"):
        return {"ok": False, "say": f"{tid}: не открытый билет исполнителя"}
    if "окружение" in reason[:40].lower():
        return {"ok": False, "say": f"{tid}: сдался из-за окружения — ступень не засчитана"}
    t["status"] = "failed"
    project.log("giveup", ticket=tid, kind=t["kind"], target=t["target"], model=t["model"], reason=reason[:600])
    escalate(state, t, [Finding("сдался", reason[:600])])
    return {"ok": True}


def recard(project, state, files, comment=""):
    """Владелец чинит карточки листьев, которые ещё не собраны, — когда из отчёта субагента видно, что карточка
    неисполнима (у входа нет предела, занижено D). Связка родителя и собранные узлы не меняются; проверка — та же,
    что у разложения родителя; открытые билеты листа снимаются, лестница — с начала."""
    from .checks import Finding
    package = state["package"]
    files = {k.replace("\\", "/").lstrip("./"): v for k, v in files.items()}
    targets = {}
    for rel in files:
        module = module_of(rel)
        node = state["nodes"].get(module)
        if not rel.endswith(".py") or node is None or node["kind"] != "leaf" or node["status"] != "card":
            return {"ok": False, "report": [f"{rel}: чинить так можно только карточки ещё не собранных листьев"]}
        targets[rel] = module
    if not targets:
        return {"ok": False, "report": ["нет файлов"]}
    stages = []
    try:
        stage = project.stage()
        stages.append(stage)
        for rel, text in files.items():
            (stage / rel).write_text(text, encoding="utf-8", newline="\n")
        pkg_files = {str(p.relative_to(stage)).replace("\\", "/"): p.read_text(encoding="utf-8") for p in (stage / package).rglob("*.py")}
        imported = checks.third_party(pkg_files, package)
        (stage / "pyproject.toml").write_text(rules.pyproject(package, rules.io_modules(pkg_files), [checks.dist_of(n) for n in imported], imported),
                                              encoding="utf-8", newline="\n")
        found = []
        for parent in sorted({state["nodes"][m]["parent"] for m in targets.values()}):
            own = str(project.path_of(parent)).replace("\\", "/")
            frozen = {name: digest for key, digest in state["cards"].items() for m, _, name in [key.partition(":")] if m == parent}
            kids = [rel for rel, m in targets.items() if state["nodes"][m]["parent"] == parent]
            found += checks.design(stage, package, parent, own, kids, frozen)
        if found:
            project.log("recard", files=sorted(files), ok=False, report=[str(f) for f in found])
            return {"ok": False, "report": [str(f) for f in found]}
        project.apply(stage, [*targets, "pyproject.toml"])
    finally:
        for s in stages:
            project.discard(s)
    for rel, module in targets.items():
        for key in [k for k in state["cards"] if k.split(":")[0] == module]:
            state["cards"].pop(key)
        for c in cards.cards(files[rel]):
            state["cards"][f"{module}:{c.name}"] = c.digest
        state["nodes"][module]["rung"] = 0
        for t in state["tickets"].values():
            if t["target"] == module and t["status"] == "open":
                t["status"] = "cancelled"
    project.log("recard", files=sorted(files), ok=True, comment=comment)
    return {"ok": True, "report": [], "say": "карточки заменены — kit_next выдаст листья заново, с первой ступени"}


def reopen(project, state, module, why, report=(), comment=""):
    """Владелец возвращает собранный узел на починку, когда дефект виден уже после сборки (полный прогон тестов нашёл
    вход, который случайные проверки сдачи пропустили). Составной узел — билет починки его проектировщику (заплатка:
    несменённые дети остаются собранными), корень — архитектору; лист — исполнителю заново с первой ступени (карточка
    верна, неверен код). Узел и все его предки снова ждут сборки с настоящими детьми; фаза — build."""
    node = state["nodes"].get(module)
    if node is None or node["kind"] not in ("leaf", "composite"):
        return {"ok": False, "say": f"{module}: такого узла с кодом нет"}
    if state["blocked"] or state["phase"] in ("architecture", "approval"):
        return {"ok": False, "say": f"сейчас вернуть узел нельзя (фаза {state['phase']}, блокировка {bool(state['blocked'])})"}
    if open_ticket(state, module):
        return {"ok": False, "say": f"{module}: у узла уже есть открытый билет"}
    up = parent_of(module)
    while up:
        if state["nodes"].get(up, {}).get("status") == "done":
            state["nodes"][up]["status"] = "designed"
        up = parent_of(up)
    state["phase"] = "build"
    found = list(report)
    if node["kind"] == "leaf":
        node["status"], node["rung"] = "card", 0
        tid = issue(state, "implement", module, ladder(state, "implement", 0), why=why, report=found, note=comment)
    elif module == state["package"]:
        # корень возвращает себе сам архитектор — это не неудачная починка, лимит починок не трогается (14.10: четыре
        # заплатки корня подряд — порог, перенос, скорость — заблокировали корень)
        node["status"] = "designed"
        state["phase"] = "architecture"
        tid = issue(state, "architect", module, "opus", why=why, report=found, note=comment)
    else:
        node["status"] = "designed"
        tid = revise(state, module, why, found, comment)
    project.log("reopen", node=module, why=why, ticket=tid, comment=comment)
    if tid is None:
        return {"ok": True, "say": f"{module}: лимит починок исчерпан — kit_next вернёт blocked"}
    return {"ok": True, "ticket": tid, "say": f"{module}: возвращён на починку — kit_next (или rptg_kit.run) выдаст билет"}


def same_card(built, sent):
    if built == sent:
        return True
    try:
        return cards.as_card(built) == cards.as_card(sent)
    except SyntaxError:
        return False


def function_names(source):
    return [fn.name for fn in ast.parse(source).body if isinstance(fn, ast.FunctionDef)]
