"""Операторы: смоук (`rptg models test`) и калибровка (`rptg models calibrate`) — ARCHITECTURE §5.1, §5.2,
LOGIC §6.4.

Смоук — механизм мицелия (lab/smoke_new_models.py по MODELS_ONBOARDING §5) поверх ядра: две задачи тем же
путём, что в работе (render_call → llm → read_answer → apply_event). Ответ JSON — карта крошечного замысла,
вердикт формы П1; код — функция пробной задачи: Э1 в ядре, тесты со скрытыми случаями в песочнице. У
llama.cpp ещё шаблон чата: промпт берётся ровно таким, каким библиотека отдаёт его модели (create_completion
подменяется на время одного вызова), и проверяются шаблон в GGUF, двойной BOS, видна ли системная часть, нет
ли в ответах чужого хода. Итог — по отпечатку оператора (D16) в ~/.rptg/smoke.json; без пройденного смоука
оператор не калибруется (§5.1).

Калибровка — круг оболочки над calibration_plan и competence. До прогона эталон каждой задачи (solution в файле
набора) проходит те же проверки, что ответы операторов: задача, отвергающая свой эталон, останавливает калибровку.
Задача плана — вызов модели на карточке эталонной задачи; функцию извлекает ядро (apply_event, Э1), тесты собирает build_files — скрытые случаи
добавлены к примерам карточки, модель их не видела; песочница гоняет всё: mypy, примеры, свойства. Итог
{item, class, operator, passed, cost, finish_reason} дописывается в ~/.rptg/calibration/<набор>/results.jsonl;
сделанная пара (задача, оператор с тем же отпечатком) не повторяется — повтор платный, `--fresh` начинает
заново, прежние итоги не удаляются. Таблица — competence по итогам операторов прогона → ~/.rptg/competence.json.
"""
import copy
import hashlib
import json
import re
import time
from pathlib import Path

import yaml

import rptg
from rptg import _types as T
from rptg._values import dump, load

from . import llm, loop, sandbox, store

PROBE_IDEA = "Функция add складывает два целых числа и возвращает их сумму."
PROBE_EXAMPLES = {"probe:add": [{"in": {"a": 2, "b": 3}, "out": 5, "source": "user"},
                                {"in": {"a": -4, "b": 4}, "out": 0, "source": "user"}]}
PROBE_ITEM = {"id": "probe-add", "class": "compute",
              "card": {"id": "probe.add", "owner": "probe", "purpose": "сумма двух целых", "uses": [], "effects": [],
                       "allowed_imports": [], "est_lines": 3,
                       "ops": [{"name": "add", "doc": "a + b", "params": [{"name": "a", "type": "integer"}, {"name": "b", "type": "integer"}],
                                "result": "integer", "requires": [], "ensures": ["result == a + b"], "effects": [],
                                "examples": [{"in": {"a": 2, "b": 3}, "out": 5, "source": "model"}]}]},
              "hidden_tests": {"cases": [{"in": {"a": -7, "b": 7}, "out": 0}, {"in": {"a": 40, "b": 2}, "out": 42}]}}
# чужой ход в сыром ответе — шаблон не применился или стоп не объявлен (MODELS_ONBOARDING §3–§5)
TURNS = ("<start_of_turn>", "<end_of_turn>", "<|start_header_id|>", "<|eot_id|>", "<|im_start|>", "<|im_end|>", "<|user|>", "[INST]")
RESULT = ("item", "class", "operator", "passed", "cost", "finish_reason")


def fingerprint(op):
    """Оператор — модель плюс то, что меняет её поведение (D16): поставщик, модель, адрес, способ вывода, шаги,
    параметры, версия подсказок; цены — нет."""
    keys = ("provider", "model", "base_url", "output_mode", "steps", "params", "prompt_version")
    return hashlib.sha256(json.dumps({k: op.get(k) for k in keys}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def blank(**more):
    """Состояние ядра без проекта: пробы и задачи калибровки живут вне .rptg/ проекта."""
    return {"phase": "NEW", "idea": "", "map_text": "", "cards": {}, "designs": {}, "types": {}, "code": {}, "evidence": {},
            "elements": {}, "approvals": {}, "user_examples": {}, "budget": {"limit": "1000000", "spent": "0"}, **more}


def item_state(item, hidden=False):
    """Состояние задачи калибровки: её карточка и карточки предков (сборке нужны их пакеты). hidden — скрытые
    случаи добавлены к примерам операции: так их прогонит песочница, а модель их не видела."""
    card = copy.deepcopy(item["card"])
    if hidden:
        card["ops"][0]["examples"] += [{**case, "source": "user"} for case in item["hidden_tests"]["cases"]]
    parts, cards = card["id"].split("."), {card["id"]: card}
    for i in range(1, len(parts)):
        node = ".".join(parts[:i])
        cards[node] = {**copy.deepcopy(item["card"]), "id": node, "owner": ".".join(parts[:i - 1]) if i > 1 else node,
                       "purpose": "эталонный набор калибровки"}
        cards[node].pop("parent", None)
    return blank(phase="BUILD", cards=cards)


def ask(core, state, task, send, calls):
    """Один вызов тем же путём, что в круге: запрос ядра, вызов, разбор конверта."""
    request = dump(rptg.render_call(task=load(T.Task, task), state=load(T.State, state), cfg=core.cfg_t))
    raw = send(task, request, core.cfg["operators"][task["operator"]])
    store.save_call(calls, task, request, raw)
    return request, dump(rptg.read_answer(provider=request["provider"], raw=raw))


def passed(out):
    """Прогон песочницы прошёл: отчёт есть, mypy чист, примеры есть и все сошлись, свойства тоже. Код выхода 0 у
    прогонщика значит лишь «отчёт записан»."""
    report = out["report"] or {}
    rows = report.get("examples", []) + report.get("properties", [])
    return out["exit_code"] == 0 and not out["timed_out"] and not (report.get("mypy") or {}).get("errors") \
        and bool(report.get("examples")) and all(r["ok"] for r in rows)


def task_of(item, op_id):
    return {"subject": f"function:{item['card']['id']}:{item['card']['ops'][0]['name']}", "kind": "function", "role": "implementer",
            "operator": op_id, "attempt": 1, "wording": "primary"}


def judge(core, item, task, answer):
    """Ответ на задачу калибровки → прошёл ли, цена, прогон: функцию извлекает ядро (apply_event, Э1 — код записан
    в состояние), тесты со скрытыми случаями гоняет песочница."""
    subject = task["subject"]
    key = subject.split(":", 1)[1]
    tr = core.apply(item_state(item), {"kind": "model_answered", "task": task, "answer": answer})
    code, out = tr["state"]["code"].get(key), None
    if code:
        state = {**item_state(item, hidden=True), "code": {key: code}}
        target = load(T.BuildTarget, {"kind": "function_tests", "subject": key})
        out = sandbox.run(dump(rptg.build_files(state=load(T.State, state), target=target, cfg=core.cfg_t))["files"], "smoke")
    return bool(out) and passed(out), (tr["state"]["elements"].get(subject) or {}).get("cost") or "0", out


def solve(core, item, task, send, calls):
    """Задача калибровки: ответ модели и его суд. Итог — запись CalibrationResult, ответ и прогон песочницы."""
    _, answer = ask(core, item_state(item), task, send, calls)
    ok, cost, out = judge(core, item, task, answer)
    return ({"item": item["id"], "class": item["class"], "operator": task["operator"], "passed": ok, "cost": cost,
             "finish_reason": answer["finish_reason"]}, answer, out)


def verify(core, ref, op_id, run):
    """Эталон задачи (solution в файле набора) проходит те же проверки, что ответы операторов: Э1, mypy, примеры,
    скрытые случаи, свойства. Задача, отвергающая собственный эталон, ничего не меряет: в эксп. 2 базы 60 %
    запустившихся наборов тестов отвергли эталон. Итог — (не прошли, без эталона); прошедшие помнятся по хэшу
    задачи в verified.json."""
    path = run / "verified.json"
    known = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    bad, unchecked = [], []
    for item in ref["items"]:
        if not item.get("solution"):
            unchecked.append(item["id"])
            continue
        digest = hashlib.sha256(json.dumps({k: item[k] for k in ("card", "hidden_tests", "solution")}, sort_keys=True,
                                           ensure_ascii=False).encode("utf-8")).hexdigest()
        if known.get(item["id"]) == digest:
            continue
        answer = {"text": "```python\n" + item["solution"].rstrip("\n") + "\n```\n", "input_tokens": 0, "output_tokens": 0,
                  "cache_read_tokens": 0, "finish_reason": "reference", "refusal": False}
        if judge(core, item, task_of(item, op_id), answer)[0]:
            known[item["id"]] = digest
        else:
            bad.append(item["id"])
    store.write_atomic(path, json.dumps(known, ensure_ascii=False, indent=1))
    return bad, unchecked


class _Prompt(Exception):
    """токены промпта, перехваченные до модели"""


def template(op, request, texts):
    """Шаблон чата llama.cpp (MODELS_ONBOARDING §5): промпт — ровно тот, что библиотека отдала бы модели; шаблон в
    GGUF или формат, заданный вручную (params.chat_format); двойной BOS; видна ли системная часть; чужой ход в
    ответах."""
    model, call = llm.model(dict(request["payload"]), op)

    def grab(prompt=None, **_):
        raise _Prompt(prompt)

    model.create_completion = grab
    try:
        model.create_chat_completion(messages=call["messages"], max_tokens=1)
        tokens = []
    except _Prompt as p:
        tokens = list(p.args[0])
    finally:
        del model.create_completion
    md, system = model.metadata, call["messages"][0]["content"]
    bos = int(md.get("tokenizer.ggml.bos_token_id", -1))
    text = model.detokenize(tokens, special=True).decode("utf-8", "replace")
    manual = "chat_format" in (op.get("params") or {})
    report = {"chat_format": model.chat_format, "gguf_template": len(md.get("tokenizer.chat_template") or ""), "manual": manual,
              "architecture": md.get("general.architecture"), "double_bos": len(tokens) > 1 and tokens[0] == tokens[1] == bos,
              "system_visible": bool(system) and system[:60] in text, "turns": sorted({t for x in texts for t in TURNS if t in x}),
              "prompt": text[:3000]}
    report["ok"] = (report["gguf_template"] > 0 or manual) and not report["double_bos"] and report["system_visible"] and not report["turns"]
    return report


def smoke(core, op_id, send, home=None, say=lambda *_: None):
    """`rptg models test <оператор>`: ответ JSON (карта крошечного замысла — вердикт формы П1), код (функция пробной
    задачи — Э1 и тесты в песочнице), у llama.cpp — шаблон чата. Итог пишется по отпечатку оператора."""
    home = home or store.home()
    op = core.cfg["operators"][op_id]
    fp = fingerprint(op)
    calls = home / "smoke" / f"{op_id}-{fp}"
    probe = loop.Core({**core.cfg, "roles": {**core.cfg["roles"], "architect": [op_id]}, "overrides": {}}, store.EMPTY_TABLE)
    state = blank(idea=PROBE_IDEA, user_examples=copy.deepcopy(PROBE_EXAMPLES))
    task = probe.next(state)["task"]
    say(f"{op_id}: карта пробного замысла (ответ JSON)…")
    t0 = time.monotonic()
    request, answer = ask(probe, state, task, send, calls)
    t1 = time.monotonic()
    tr = probe.apply(state, {"kind": "model_answered", "task": task, "answer": answer})
    form = [e["verdict"] for e in tr["evidence"] if e["check"] == "P1"]
    say(f"{op_id}: функция пробной задачи (код)…")
    t2 = time.monotonic()
    code, code_answer, out = solve(probe, PROBE_ITEM, task_of(PROBE_ITEM, op_id), send, calls)
    report = {"operator": op_id, "fingerprint": fp, "provider": op["provider"], "model": op["model"], "at": store.now(),
              "json": {"form": form, "ok": form == ["pass"], "finish_reason": answer["finish_reason"], "seconds": round(t1 - t0),
                       "tokens": [answer["input_tokens"], answer["output_tokens"]], "text": answer["text"][:3000]},
              "code": {**code, "seconds": round(time.monotonic() - t2), "text": code_answer["text"][:3000], "sandbox": out and out["report"]}}
    if op["provider"] == "llamacpp":
        report["template"] = template(op, request, [answer["text"], code_answer["text"]])
    report["passed"] = report["json"]["ok"] and code["passed"] and report.get("template", {"ok": True})["ok"]
    store.write_atomic(calls / "report.json", json.dumps(report, ensure_ascii=False, indent=1))
    index = json.loads((home / "smoke.json").read_text(encoding="utf-8")) if (home / "smoke.json").exists() else {}
    index[fp] = {k: report[k] for k in ("operator", "provider", "model", "at", "passed")}
    store.write_atomic(home / "smoke.json", json.dumps(index, ensure_ascii=False, indent=1))
    return report


def core_set(ref):
    """Набор для ядра: без эталонных решений — их видит только оболочка."""
    return {"name": ref["name"], "items": [{k: v for k, v in item.items() if k != "solution"} for item in ref["items"]]}


def reference(name):
    """Эталонный набор: путь к файлу YAML или JSON, иначе ~/.rptg/reference/<имя>.yaml|.json (ARCHITECTURE §3). У
    задачи, кроме полей ReferenceItem, может быть solution — эталонное решение для проверки самой задачи."""
    path = Path(name)
    if not path.is_file():
        path = next((p for p in (store.home() / "reference" / f"{name}{ext}" for ext in (".yaml", ".yml", ".json")) if p.is_file()), None)
        if path is None:
            raise ValueError(f"нет эталонного набора «{name}»: укажите файл или положите ~/.rptg/reference/{name}.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    load(T.ReferenceSet, core_set(data))
    return data


def calibrate(core, op_ids, ref, send, say=print, home=None, fresh=False):
    """`rptg models calibrate`: каждый оператор на каждой задаче набора (LOGIC §6.4), итоги — по одному на пару,
    таблица — по итогам операторов этого прогона с их нынешними отпечатками."""
    home = home or store.home()
    prints = {o: fingerprint(core.cfg["operators"][o]) for o in op_ids}
    smoked = json.loads((home / "smoke.json").read_text(encoding="utf-8")) if (home / "smoke.json").exists() else {}
    missing = [o for o in op_ids if not (smoked.get(prints[o]) or {}).get("passed")]
    if missing:
        raise ValueError(f"без пройденного смоука: {', '.join(missing)} — сначала `rptg models test <имя>` (ARCHITECTURE §5.1)")
    untrusted = sorted({"E1", "E2", "E3"} - set(core.cfg.get("trusted") or []))
    if untrusted:
        raise ValueError(f"проверки {', '.join(untrusted)} не доверены — сначала `rptg selftest`")
    run = home / "calibration" / re.sub(r"[^\w.-]+", "_", ref["name"])
    bad, unchecked = verify(core, ref, op_ids[0], run)
    if bad:
        raise ValueError(f"эталон не проходит проверки своей задачи: {', '.join(bad)} — такая задача ничего не меряет; "
                         "поправьте карточку, скрытые случаи или решение")
    if unchecked:
        say(f"без эталона (solution), задача не проверена: {', '.join(unchecked)}")
    plan = dump(rptg.calibration_plan(reference=load(T.ReferenceSet, core_set(ref)), operators=op_ids, cfg=core.cfg_t))
    path = run / "results.jsonl"
    if fresh and path.exists():
        path.rename(path.with_name("results-" + re.sub(r"\D", "", store.now()) + ".jsonl"))
    done = {(r["item"], r["operator"], r["fingerprint"]) for r in store.read_rows(path)}
    for i, task in enumerate(plan["tasks"]):
        item = ref["items"][i // len(op_ids)]
        if (item["id"], task["operator"], prints[task["operator"]]) in done:
            continue
        result, _, _ = solve(core, item, task, send, run / "calls")
        store.append_rows(path, [{**result, "fingerprint": prints[task["operator"]], "at": store.now()}])
        say(f"{item['id']:<20} {task['operator']:<12} {'прошла' if result['passed'] else 'не прошла':<10} цена {result['cost']}, "
            f"{result['finish_reason']}")
    mine = [{k: r[k] for k in RESULT} for r in store.read_rows(path) if prints.get(r["operator"]) == r["fingerprint"]]
    table = dump(rptg.competence(results=load(T.CalibrationResults, mine), plan=load(T.CalibrationPlan, plan), cfg=core.cfg_t))
    store.write_atomic(home / "competence.json", json.dumps(table, ensure_ascii=False, indent=1))
    return table
