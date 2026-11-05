"""Командная строка rptg (ARCHITECTURE §8).

    rptg new <папка> --idea "…" --examples примеры.yaml [--preset claude|mixed|local] [--budget 20.00]
    rptg run [--until map|design|build] [--steps N]
    rptg approve [--reject "комментарий"] | decide <предмет> retry|revise [--comment …] | recheck <предмет>
    rptg pause | resume | budget <лимит>
    rptg status | show <узел> | graph | outcomes
    rptg export [--to <папка>]          собранная программа в <проект>/src (и сама по окончании run)
    rptg gui [--port N] [--no-browser]  окно на 127.0.0.1 с токеном
    rptg assign <маска> --role implementer --model <оператор>   ручное назначение (LOGIC §6.6)
    rptg models test <оператор>         смоук: строгий JSON, код, у llama.cpp — шаблон чата
    rptg models calibrate <оператор>… [--set functions] [--fresh]   калибровка на эталонном наборе
    rptg selftest

Ответы пользователя и команды — события ядру: состояние меняет только apply_event.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

import rptg
from rptg import _types as T
from rptg._values import dump, load

from . import llm, loop, presets, store


def new(args):
    root = Path(args.dir)
    project = store.Project(root)
    if project.exists():
        sys.exit(f"проект уже есть: {root}")
    examples = yaml.safe_load(Path(args.examples).read_text(encoding="utf-8")) or {}
    user = {key: [{**ex, "source": "user"} for ex in rows] for key, rows in examples.items()}
    root.mkdir(parents=True, exist_ok=True)
    cfg = presets.config(args.preset)
    (root / "project.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    project.save_state({"phase": "NEW", "idea": args.idea, "map_text": "", "cards": {}, "designs": {}, "types": {}, "code": {},
                        "evidence": {}, "elements": {}, "approvals": {}, "user_examples": user,
                        "budget": {"limit": args.budget, "spent": "0"}})
    unpriced = sorted(k for k, o in cfg["operators"].items() if o["provider"] != "llamacpp" and set(o["prices"].values()) <= {"0"})
    print(f"проект создан: {root}\nцены в project.yaml — открытые данные поставщиков на {presets.PRICES_AS_OF}, у локальных моделей — 0")
    if unpriced:
        print(f"у операторов {', '.join(unpriced)} нет модели и цен: впишите их в project.yaml, иначе их расход не считается")
    print("код моделей запускается в песочнице без ограничений ОС (ARCHITECTURE §9): отдельный процесс, временная папка, "
          "тайм-аут и чистое окружение, запреты — статические (Э1); процесс работает с вашими правами")
    if not store.Project(root).config().get("trusted"):
        print("доверенных проверок нет — запустите `rptg selftest`, иначе ни один ответ не будет принят (ERROR ≠ FAIL)")


def answer(project, event):
    with project.lock():
        core = loop.Core(project.config(), project.table())
        state = loop.apply(project, core, project.load_state(), event)
    print(f"фаза: {state['phase']}")


def approve(project, args):
    core = loop.Core(project.config(), project.table())
    action = core.next(project.load_state())
    question = action.get("question") or {}
    if "approve" not in question:
        sys.exit("нечего утверждать")
    reply = {**question, "decision": "no" if args.reject else "yes", "comment": args.reject or ""}
    answer(project, {"kind": "user_answered", "reply": reply})


def export(project, to=None):
    out, n = loop.export(project, loop.Core(project.config(), project.table()), project.load_state(), Path(to) if to else None)
    print(f"программа выгружена: {out} ({n} файлов); проверить — `python run_tests.py all` в этой папке")


def tell(project, action):
    """Что ядро ждёт от пользователя после круга; конец — выгрузка программы."""
    q = action.get("question") or {}
    if action["kind"] == "stop":
        print("готово: программа собрана и принята")
        export(project)
    elif "approve" in q:
        print(f"утвердите разложение {q['approve']}: `rptg graph`, `rptg show {q['approve']}`; затем `rptg approve` или `rptg approve --reject \"…\"`")
    elif "recheck" in q:
        print(f"{q['recheck']}: проверки не уверены (unknown) — `rptg selftest`, затем `rptg recheck {q['recheck']}`")
    elif "decide" in q:
        print(f"{q['decide']} ждёт решения ({q['reason']}): `rptg decide {q['decide']} retry|revise [--comment …]`")
        print(json.dumps(q.get("reports", []), ensure_ascii=False, indent=1))
    else:
        print(f"пауза: {action.get('reason', '')}")


def smoke(project, operator):
    from . import models
    r = models.smoke(loop.Core(project.config(), project.table()), operator, llm.send, say=print)
    j, c, t = r["json"], r["code"], r.get("template")
    print(f"оператор {operator} ({r['provider']} {r['model']}), отпечаток {r['fingerprint']}")
    print(f"  JSON (карта пробного замысла): форма П1 — {', '.join(j['form']) or 'нет вердикта'}; finish_reason {j['finish_reason']}; "
          f"токены {j['tokens'][0]} → {j['tokens'][1]}; {j['seconds']} с")
    print(f"  код (функция add): {'прошёл' if c['passed'] else 'НЕ прошёл'} — Э1, mypy, примеры и скрытые случаи; finish_reason "
          f"{c['finish_reason']}; цена {c['cost']}; {c['seconds']} с")
    if t:
        print(f"  шаблон чата: формат {t['chat_format']}, шаблон в GGUF — {t['gguf_template']} символов{', задан вручную' if t['manual'] else ''}; "
              f"двойной BOS — {'ДА' if t['double_bos'] else 'нет'}; системная часть видна — {'да' if t['system_visible'] else 'НЕТ'}; "
              f"чужой ход в ответах — {', '.join(t['turns']) or 'нет'}")
        print("  промпт после шаблона — смотреть глазами (MODELS_ONBOARDING §5):\n    " + t["prompt"][:800].replace("\n", "\n    "))
    print("смоук пройден" if r["passed"] else "смоук НЕ пройден — оператор не калибруется (ARCHITECTURE §5.1)")
    print(f"подробности: {store.home() / 'smoke' / (operator + '-' + r['fingerprint']) / 'report.json'}")


def calibrate(project, args):
    from . import models
    table = models.calibrate(loop.Core(project.config(), project.table()), args.operators, models.reference(args.set), llm.send,
                             fresh=args.fresh)
    print(f"таблица компетенций — {store.home() / 'competence.json'}; маршрут по роду (G0): {'да' if table['g0'] else 'нет'}")
    for c in table["cells"]:
        print(f"  {c['class']:<10} {c['operator']:<12} подбор {c['ok_fit']}/{c['n_fit']}, проверка {c['ok_check']}/{c['n_check']}, "
              f"цена на успех {c['cost_per_success']}{' — мало данных' if c['low_data'] else ''}")


def selftest():
    cases = json.loads((Path(__file__).with_name("control_cases.json")).read_text(encoding="utf-8"))
    report = rptg.selftest(cases=load(T.ControlCases, cases), cfg=load(T.Config, presets.config("claude")))
    trusted = [r.check for r in report.checks if r.trusted]
    store.write_atomic(store.home() / "trusted.json", json.dumps(trusted))
    for r in report.checks:
        print(f"{r.check:<3} сошлось {r.passed:>3}, не сошлось {r.failed}, {'доверена' if r.trusted else 'НЕ доверена'}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="rptg")
    p.add_argument("--project", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("dir")
    n.add_argument("--idea", required=True)
    n.add_argument("--examples", required=True)
    n.add_argument("--preset", default="claude", choices=sorted(presets.PRESETS))
    n.add_argument("--budget", default="20.00")
    r = sub.add_parser("run")
    r.add_argument("--until", choices=sorted(loop.UNTIL))
    r.add_argument("--steps", type=int, default=1000)
    sub.add_parser("approve").add_argument("--reject")
    d = sub.add_parser("decide")
    d.add_argument("subject")
    d.add_argument("decision", choices=["retry", "revise"])
    d.add_argument("--comment", default="")
    sub.add_parser("recheck").add_argument("subject")
    for name in ("pause", "resume", "status", "graph", "outcomes", "selftest"):
        sub.add_parser(name)
    sub.add_parser("budget").add_argument("limit")
    sub.add_parser("show").add_argument("node")
    sub.add_parser("export").add_argument("--to")
    g = sub.add_parser("gui")
    g.add_argument("--port", type=int, default=0)
    g.add_argument("--no-browser", action="store_true")
    a = sub.add_parser("assign")
    a.add_argument("mask")
    a.add_argument("--role", required=True, choices=["designer", "implementer"])
    a.add_argument("--model", required=True, help="оператор из лестницы роли")
    m = sub.add_parser("models").add_subparsers(dest="models_cmd", required=True)
    m.add_parser("test").add_argument("operator")
    c = m.add_parser("calibrate")
    c.add_argument("operators", nargs="+")
    c.add_argument("--set", default="functions", help="файл набора или имя в ~/.rptg/reference/")
    c.add_argument("--fresh", action="store_true", help="заново: прежние итоги остаются в отдельном файле")
    args = p.parse_args(argv)

    if args.cmd == "new":
        return new(args)
    if args.cmd == "selftest":
        return selftest()
    project = store.Project(args.project)
    if not project.exists():
        sys.exit(f"нет проекта rptg в {Path(args.project).resolve()}")
    events = {"decide": lambda: {"kind": "user_answered", "reply": {"decide": args.subject, "decision": args.decision, "comment": args.comment}},
              "recheck": lambda: {"kind": "user_answered", "reply": {"recheck": args.subject}},
              "pause": lambda: {"kind": "command", "reply": {"command": "pause"}},
              "resume": lambda: {"kind": "command", "reply": {"command": "resume"}},
              "budget": lambda: {"kind": "command", "reply": {"command": "budget", "limit": args.limit}}}
    try:
        if args.cmd in events:
            return answer(project, events[args.cmd]())
        if args.cmd == "approve":
            return approve(project, args)
        if args.cmd == "run":
            with project.lock():
                action = loop.run(project, until=args.until, steps=args.steps)
            return tell(project, action)
        if args.cmd == "assign":
            store.assign(project.root, args.mask, args.role, args.model)
            return print(f"закреплено в project.yaml: {args.mask} → {args.role}: {args.model} (действует на ещё не начатые задачи)")
        if args.cmd == "models":
            unknown = sorted({getattr(args, "operator", None), *getattr(args, "operators", [])} - {None} - set(project.config()["operators"]))
            if unknown:
                sys.exit(f"нет операторов {', '.join(unknown)} в project.yaml")
            try:
                return smoke(project, args.operator) if args.models_cmd == "test" else calibrate(project, args)
            except (store.Busy, ValueError):
                raise
            except (RuntimeError, OSError) as e:  # нет ключа, сбой сети или модели — без трассировки; сделанное записано
                sys.exit(f"прервано: {type(e).__name__}: {e}")
    except (store.Busy, ValueError) as e:
        sys.exit(str(e))
    if args.cmd == "export":
        return export(project, args.to)
    if args.cmd == "gui":
        from . import gui
        server, app = gui.serve(project, args.port)
        print(f"окно: {app.url}\n(доступ только по этому адресу с токеном; остановка — Ctrl+C)")
        if not args.no_browser:
            import webbrowser
            webbrowser.open(app.url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return None
    core = loop.Core(project.config(), project.table())
    kind, subject = {"status": ("status", None), "show": ("node", getattr(args, "node", None)), "graph": ("graph", None),
                     "outcomes": ("competence", None)}[args.cmd]
    data = core.view(project.load_state(), kind=kind, **({"subject": subject} if subject else {}))["data"]
    print(json.dumps(data, ensure_ascii=False, indent=1))
