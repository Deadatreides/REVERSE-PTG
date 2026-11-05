"""Круг оболочки (map.md §1, ARCHITECTURE §4): plan_next → действие → событие → apply_event.

Ядро решает, оболочка исполняет: вызов модели (render_call → llm → read_answer), прогон песочницы
(build_files → sandbox). Вопрос пользователю, пауза и конец останавливают круг — ответ даёт команда
(approve, decide, recheck, resume…), и следующий `run` продолжает с сохранённого состояния. Совпавший по
хэшу ответ — не попытка: при новом вызове того же задания оболочка меняет зерно у поставщиков, где оно есть
(LOGIC §7.3). У Anthropic зерна нет, а температуру новые модели не принимают (Opus 5.5 — 400): повтор уходит
как есть, ответы и так различаются при температуре по умолчанию; потолок повторам — BUDGET политики.
"""
from rptg import _types as T
from rptg._values import dump, load

import rptg

from . import llm, sandbox, store

PHASES = ["NEW", "MAP", "MAP_REVIEW", "DESIGN", "BUILD", "E2E", "DONE"]
UNTIL = {"map": "MAP_REVIEW", "design": "BUILD", "build": "E2E"}
SEEDED = {"openai", "openrouter", "openai_compatible", "llamacpp"}


class Core:
    """Ядро над словарями JSON: типы — только на границе вызова."""

    def __init__(self, cfg, table):
        self.cfg, self.cfg_t, self.table_t = cfg, load(T.Config, cfg), load(T.Competence, table)

    def next(self, state):
        return dump(rptg.plan_next(state=load(T.State, state), cfg=self.cfg_t, table=self.table_t))

    def apply(self, state, event):
        return dump(rptg.apply_event(state=load(T.State, state), event=load(T.Event, event), cfg=self.cfg_t))

    def view(self, state, **query):
        return dump(rptg.view(state=load(T.State, state), query=load(T.ViewQuery, query), cfg=self.cfg_t))


def reseed(request, repeats):
    """Новое зерно на повторе: у OpenAI-подобных и llama.cpp — аргумент seed, у Google — config.seed; у
    остальных запрос не меняется."""
    if not repeats:
        return request
    payload, seed = request["payload"], 1000 + repeats
    if request["provider"] in SEEDED:
        return {**request, "payload": {**payload, "seed": seed}}
    if request["provider"] == "google":
        return {**request, "payload": {**payload, "config": {**payload.get("config", {}), "seed": seed}}}
    return request


def call_model(project, core, state, task, send):
    request = dump(rptg.render_call(task=load(T.Task, task), state=load(T.State, state), cfg=core.cfg_t))
    repeats = sum(1 for j in project.journal() if j.get("kind") == "repeat" and j.get("subject") == task["subject"])
    request = reseed(request, repeats)
    raw = send(task, request, core.cfg["operators"][task["operator"]])
    project.save_call(task, request, raw)
    return {"kind": "model_answered", "task": task, "answer": dump(rptg.read_answer(provider=request["provider"], raw=raw))}


def run_sandbox(core, state, action):
    files = dump(rptg.build_files(state=load(T.State, state), target=load(T.BuildTarget, action["target"]), cfg=core.cfg_t))["files"]
    return {"kind": "sandbox_finished", "target": action["target"], "output": sandbox.run(files, action["run"])}


def export(project, core, state, out=None):
    """Собранная программа целиком — файлы цели program корня (пакет, тесты, run_tests.py) в <проект>/src."""
    root = next((c for c in state["cards"] if "." not in c), "")
    target = load(T.BuildTarget, {"kind": "program", "subject": root})
    files = dump(rptg.build_files(state=load(T.State, state), target=target, cfg=core.cfg_t))["files"]
    out = out or project.root / "src"
    for path, text in files.items():
        store.write_atomic(out / path, text)
    return out, len(files)


def apply(project, core, state, event):
    tr = core.apply(state, event)
    project.record(event, tr)
    project.save_state(tr["state"])
    return tr["state"]


def run(project, until=None, steps=1000, send=llm.send, say=print, stop=lambda: False):
    """Круг до вопроса, паузы, конца, фазы until, предела шагов или просьбы остановиться (окно); итог —
    последнее действие ядра."""
    core = Core(project.config(), project.table())
    state = project.load_state()
    for _ in range(steps):
        if until and PHASES.index(state["phase"]) >= PHASES.index(UNTIL[until]):
            return {"kind": "pause", "reason": f"дошли до {state['phase']} (--until {until})"}
        if stop():
            return {"kind": "pause", "reason": "остановлено пользователем"}
        action = core.next(state)
        if action["kind"] not in ("call_model", "run_sandbox"):
            return action
        say(f"{state['phase']:<10} {action['kind']} " + (action["task"]["subject"] if "task" in action else action["target"]["subject"]))
        try:
            event = call_model(project, core, state, action["task"], send) if action["kind"] == "call_model" else run_sandbox(core, state, action)
        except Exception as e:  # сбой сети или ключа — не ответ модели: ядру его не отдать, круг встаёт
            return {"kind": "pause", "reason": f"сбой исполнения: {type(e).__name__}: {e}"}
        state = apply(project, core, state, event)
    return {"kind": "pause", "reason": f"предел шагов {steps}"}
