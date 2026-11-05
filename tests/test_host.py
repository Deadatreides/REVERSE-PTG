"""Оболочка rptg_host: сквозной круг командами и ядром, хранилище, песочница, ключи.

Модель подменена записанными ответами в конверте Anthropic (карта и разложения — вызов инструмента answer,
код — текст с блоком python); всё остальное настоящее: ядро, check, песочница с run_tests.py. Домашняя
папка rptg — временная (RPTG_HOME), ключи API в тестах не нужны и не пишутся.

    python -m pytest tests/test_host.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

import rptg  # noqa: E402
from rptg import _types as T  # noqa: E402
from rptg._values import load  # noqa: E402
from rptg_host import cli, llm, loop, presets, sandbox, store  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.plan.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["fixtures"]}


def tool(value):
    return {"content": [{"type": "tool_use", "id": "t1", "name": "answer", "input": value}]}


def text(body):
    return {"content": [{"type": "text", "text": body}]}


ANSWERS = {
    "map:app": tool({"map_text": "# Карта app\n\nДва узла: накладные и деньги.\n", "card": FX["c_app_fixed"],
                     "types": [FX["t_money"], FX["t_line"], FX["t_order"], FX["t_invoice"]]}),
    "design:app": tool({k: v for k, v in FX["d_app_fixed"].items() if k != "node"}),
    "design:app.billing": tool({k: v for k, v in FX["d_billing"].items() if k != "node"}),
    "function:app.billing.lines:line_total": text("```python\n" + FX["code_lt"] + "```\n"),
    "function:app.money:add": text("```python\n" + FX["code_add"] + "```\n"),
}


def fake_send(calls):
    def send(task, request, operator):
        calls.append((task["subject"], request["provider"]))
        return {**ANSWERS[task["subject"]], "stop_reason": "end_turn", "usage": {"input_tokens": 1000, "output_tokens": 200}}
    return send


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("RPTG_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def test_invoice_program_from_idea_to_done_by_commands(tmp_path, home, capsys):
    """selftest → new → run (до утверждения) → approve → run до DONE: настоящие ядро, check и песочница."""
    cli.main(["selftest"])
    assert len(json.loads((home / "trusted.json").read_text(encoding="utf-8"))) == 10
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({k: [{"in": e["in"], "out": e["out"]} for e in v] for k, v in FX["s_new"]["user_examples"].items()},
                                       allow_unicode=True), encoding="utf-8")
    project_dir = tmp_path / "app"
    cli.main(["new", str(project_dir), "--idea", FX["s_new"]["idea"], "--examples", str(examples)])
    project, calls = store.Project(project_dir), []

    first = loop.run(project, send=fake_send(calls), say=lambda *_: None)
    assert first["kind"] == "ask_user" and first["question"]["approve"] == "app"
    cli.main(["--project", str(project_dir), "approve"])
    last = loop.run(project, send=fake_send(calls), say=lambda *_: None)

    assert last == {"kind": "stop"} and project.load_state()["phase"] == "DONE"
    assert [s for s, _ in calls] == list(ANSWERS)
    journal = project.journal()
    assert all(row["at"] for row in journal) and {r["event"] for r in journal if "event" in r} == {"model_answered", "user_answered", "sandbox_finished"}
    saved = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((project.dir / "calls").glob("*.json"))]
    assert len(saved) == 5
    assert all(set(c["request"]) <= {"provider", "operator", "mode", "endpoint", "payload"} for c in saved)   # как ушёл: поля ProviderRequest
    assert all("api_key" not in json.dumps(c["request"]).lower() for c in saved)                             # ключей в сохранённом нет
    cli.main(["--project", str(project_dir), "status"])
    assert '"phase": "DONE"' in capsys.readouterr().out

    cli.main(["--project", str(project_dir), "export"])          # результат — программа, которая проходит свои тесты сама
    src = project_dir / "src"
    assert (src / "app" / "__init__.py").exists() and (src / "run_tests.py").exists()
    proc = subprocess.run([sys.executable, "run_tests.py", "all"], cwd=src, env=sandbox.clean_env(), capture_output=True, timeout=600)
    report = json.loads((src / "report.json").read_text(encoding="utf-8"))
    assert proc.returncode == 0 and report["examples"] and all(r["ok"] for r in report["examples"] + report["properties"])


def test_state_is_written_atomically_and_journal_appends(tmp_path):
    project = store.Project(tmp_path)
    project.save_state({"phase": "NEW"})
    project.save_state({"phase": "MAP"})
    assert project.load_state() == {"phase": "MAP"} and not list(project.dir.glob("*.tmp"))
    project.record({"kind": "command"}, {"journal": [{"kind": "phase", "subject": "", "data": {}}]})
    project.record({"kind": "command"}, {"journal": []})
    assert len(project.journal()) == 3


def test_sandbox_does_not_pass_secrets_to_model_code(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-secret")
    monkeypatch.setenv("RPTG_KEY_OPUS", "sk-test-secret")
    env = sandbox.clean_env()
    assert "sk-test-secret" not in json.dumps(env) and env["PYTHONHASHSEED"] == "0"


def test_keys_come_only_from_the_environment(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RPTG_KEY_OPUS", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm.key("anthropic", {"id": "opus"})
    monkeypatch.setenv("RPTG_KEY_OPUS", "k")
    assert llm.key("anthropic", {"id": "opus"}) == "k"
    assert llm.key("openai_compatible", {"id": "vllm"}) == "not-needed"


def test_network_failure_pauses_without_an_event(tmp_path, home):
    """Сбой сети — не ответ модели: ядру его не отдать, круг встаёт, состояние не меняется."""
    cli.main(["selftest"])
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({"app:invoice": [{"in": {"order": {"id": 1, "lines": []}}, "out": {}}]}), encoding="utf-8")
    cli.main(["new", str(tmp_path / "p"), "--idea", "x", "--examples", str(examples)])
    project = store.Project(tmp_path / "p")
    before = project.load_state()

    def broken(task, request, operator):
        raise ConnectionError("нет сети")

    action = loop.run(project, send=broken, say=lambda *_: None)
    assert action["kind"] == "pause" and "нет сети" in action["reason"] and project.load_state() == before


def small(tmp_path, idea="x"):
    """Проект с одним примером корня — для проверок оболочки без полного круга."""
    cli.main(["selftest"])
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({"app:invoice": [{"in": {"order": {"id": 1, "lines": []}}, "out": {}}]}), encoding="utf-8")
    cli.main(["new", str(tmp_path / "p"), "--idea", idea, "--examples", str(examples)])
    return store.Project(tmp_path / "p")


def test_preset_claude_request_carries_max_tokens(tmp_path, home):
    """Перепроверка 04.10: у Anthropic max_tokens обязателен (ARCHITECTURE §5.1), а talk умолчаний не вводит —
    без него в пресете первый живой вызов падал в SDK. Запрос берётся настоящим путём круга."""
    project, seen = small(tmp_path), []

    def capture(task, request, operator):
        seen.append(request)
        raise ConnectionError("стоп")

    loop.run(project, send=capture, say=lambda *_: None)
    assert seen[0]["provider"] == "anthropic" and seen[0]["payload"]["max_tokens"] == 128000
    for name in presets.PRESETS:
        assert all(op["params"]["max_tokens"] == presets.CEILING[op["model"]]
                   for op in presets.config(name)["operators"].values() if op["provider"] == "anthropic")


def test_prices_written_as_numbers_are_read(tmp_path, home):
    """`input: 4` в YAML — число, а цены ядра — записи: раньше любая команда падала на BadValue."""
    project = small(tmp_path)
    path = project.root / "project.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["operators"]["opus"]["prices"] = {"input": 4, "output": 20, "cache": 0.2}
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    core = loop.Core(project.config(), project.table())
    answer = load(T.RawAnswer, {"text": "", "input_tokens": 1000, "output_tokens": 1000, "cache_read_tokens": 1000,
                                "finish_reason": "end_turn", "refusal": False})
    assert project.config()["operators"]["opus"]["prices"] == {"input": "4", "output": "20", "cache": "0.2"}
    assert rptg.talk.cost(answer=answer, operator=core.cfg_t.operators["opus"]) == "0.0242"


def test_saved_calls_pass_secret_scrubbing(tmp_path, home):
    """ARCHITECTURE §9: тексты попыток проходят вычистку секретов (список PTG-MEM) — и в запросе, и в ответе."""
    fake = "sk-ant-api03-" + "Q" * 32
    project = small(tmp_path, idea="ключ для проверки " + fake)

    def echo(task, request, operator):
        return {"content": [{"type": "text", "text": "вот он: " + fake}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5}}

    loop.run(project, send=echo, steps=1, say=lambda *_: None)
    saved = [p.read_text(encoding="utf-8") for p in (project.dir / "calls").glob("*.json")]
    assert len(saved) == 1 and fake not in saved[0] and saved[0].count("<secret-removed:sk-") == 2
    assert store.scrub("-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----") == "<secret-removed:private-key>"
    assert store.scrub("обычный текст sk-коротко") == "обычный текст sk-коротко"


def test_repeat_changes_the_seed_where_the_provider_has_one():
    """LOGIC: совпавший ответ — не попытка, исполнитель меняет зерно. У Google оно в config, у Anthropic зерна нет."""
    base = {"provider": "openai", "operator": "x", "mode": "json_schema", "payload": {"model": "m"}}
    assert loop.reseed(base, 0) == base and loop.reseed(base, 2)["payload"]["seed"] == 1002
    google = {**base, "provider": "google", "payload": {"model": "m", "config": {"system_instruction": "s"}}}
    assert loop.reseed(google, 1)["payload"]["config"] == {"system_instruction": "s", "seed": 1001}
    anthropic = {**base, "provider": "anthropic"}
    assert loop.reseed(anthropic, 3) == anthropic and "seed" not in loop.reseed(google, 1)["payload"]


def test_llamacpp_params_split_between_loading_and_call():
    """Параметры загрузки (n_gpu_layers, chat_format…) у create_chat_completion — TypeError: делятся по
    сигнатурам самой библиотеки, seed остаётся вызову."""
    llama_cpp = pytest.importorskip("llama_cpp")
    loading, call = llm.split({"messages": [], "n_gpu_layers": 99, "chat_format": "gemma", "seed": 5, "temperature": 0.2},
                              llama_cpp.Llama)
    assert loading == {"n_ctx": 8192, "verbose": False, "n_gpu_layers": 99, "chat_format": "gemma"}
    assert call == {"messages": [], "seed": 5, "temperature": 0.2}
    assert llm.split({"n_ctx": 4096}, llama_cpp.Llama)[0]["n_ctx"] == 4096


def test_one_writer_per_project(tmp_path, home):
    """Круг и ответы держат замок проекта: второй писатель получает отказ, а не перезапись чужого перехода."""
    project = small(tmp_path)
    with project.lock():
        with pytest.raises(store.Busy):
            with project.lock():
                pass
        with pytest.raises(SystemExit, match="занят"):
            cli.main(["--project", str(project.root), "pause"])
    before = len(project.journal())
    cli.main(["--project", str(project.root), "pause"])
    assert len(project.journal()) > before


def stream_events(answer, model):
    """Ответ Messages API потоком событий (SSE), как его отдаёт сервер: начало, блок (вызов инструмента — вход
    кусками input_json_delta, текст — text_delta), конец блока, причина остановки и расход, конец."""
    block = answer["content"][0]
    if block["type"] == "tool_use":
        body = json.dumps(block["input"], ensure_ascii=False)
        start, deltas = {"type": "tool_use", "id": "toolu_1", "name": block["name"], "input": {}}, \
            [{"type": "input_json_delta", "partial_json": part} for part in (body[:len(body) // 2], body[len(body) // 2:])]
    else:
        start, deltas = {"type": "text", "text": ""}, [{"type": "text_delta", "text": block["text"]}]
    events = [("message_start", {"type": "message_start", "message": {
        "id": "msg_1", "type": "message", "role": "assistant", "model": model, "content": [], "stop_reason": None,
        "stop_sequence": None, "usage": {"input_tokens": 1000, "output_tokens": 1, "cache_read_input_tokens": 0,
                                         "cache_creation_input_tokens": 0}}}),
              ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": start})]
    events += [("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": d}) for d in deltas]
    events += [("content_block_stop", {"type": "content_block_stop", "index": 0}),
               ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "tool_use" if block["type"] == "tool_use" else "end_turn",
                                                                     "stop_sequence": None}, "usage": {"output_tokens": 200}}),
               ("message_stop", {"type": "message_stop"})]
    return "".join(f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n" for name, data in events).encode("utf-8")


def test_invoice_program_through_the_real_anthropic_sdk(tmp_path, home, monkeypatch):
    """Путь llm.send → SDK anthropic по-настоящему, без сети: транспорт httpx2.MockTransport (SDK 1.x) отдаёт
    записанные ответы потоком. SDK сам проверяет аргументы запроса, шлёт его по HTTP и собирает ответ из
    потока; ядро разбирает model_dump. Программа накладных доходит до DONE."""
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    queue, seen = list(ANSWERS.values()), []

    def server(request):
        body = json.loads(request.content)
        seen.append((request.method, request.url.path, request.headers.get("x-api-key"), body))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=stream_events(queue.pop(0), body["model"]))

    real = anthropic.Anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: real(**kw, http_client=anthropic.DefaultHttpxClient(
        transport=httpx2.MockTransport(server))))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    for name in ("OPUS", "SONNET", "HAIKU"):
        monkeypatch.delenv("RPTG_KEY_" + name, raising=False)
    cli.main(["selftest"])
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({k: [{"in": e["in"], "out": e["out"]} for e in v] for k, v in FX["s_new"]["user_examples"].items()},
                                       allow_unicode=True), encoding="utf-8")
    cli.main(["new", str(tmp_path / "app"), "--idea", FX["s_new"]["idea"], "--examples", str(examples)])
    project = store.Project(tmp_path / "app")

    first = loop.run(project, say=lambda *_: None)
    assert first["kind"] == "ask_user" and first["question"]["approve"] == "app", first
    cli.main(["--project", str(project.root), "approve"])
    assert loop.run(project, say=lambda *_: None) == {"kind": "stop"} and project.load_state()["phase"] == "DONE"

    assert len(seen) == len(ANSWERS) and not queue
    assert all(m == "POST" and path == "/v1/messages" and key == "test-key" for m, path, key, _ in seen)
    assert all(b["stream"] is True and b["max_tokens"] == presets.CEILING[b["model"]] for *_, b in seen)
    first_body = seen[0][3]
    assert first_body["model"] == "claude-opus-5-5" and first_body["tool_choice"] == {"type": "auto"}
    assert first_body["tools"][0]["name"] == "answer" and first_body["system"][0]["cache_control"] == {"type": "ephemeral"}
    spent = project.load_state()["budget"]["spent"]
    assert 0 < float(spent) < 1, spent                                     # цены пресета считаются, не «0»


def answer_text(answer):
    """Записанный ответ (конверт Anthropic) → текст: JSON-ответ целиком (способ json_schema), код — как есть."""
    block = answer["content"][0]
    return json.dumps(block["input"], ensure_ascii=False) if block["type"] == "tool_use" else block["text"]


def chat_completion(answer):
    return {"id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": answer_text(answer)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}}


def gemini_response(answer):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": answer_text(answer)}]}, "finishReason": "STOP", "index": 0}],
            "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 200, "totalTokenCount": 1200}, "modelVersion": "m"}


OTHER = {   # поставщик → оператор, переменная ключа, адрес вызова
    "openai": ({"id": "gpt", "provider": "openai", "model": "gpt-test"}, "OPENAI_API_KEY",
               "https://api.openai.com/v1/chat/completions"),
    "openrouter": ({"id": "router", "provider": "openrouter", "model": "vendor/model-test"}, "OPENROUTER_API_KEY",
                   "https://openrouter.ai/api/v1/chat/completions"),
    "openai_compatible": ({"id": "server", "provider": "openai_compatible", "model": "local-test", "base_url": "http://127.0.0.1:8080/v1"},
                          None, "http://127.0.0.1:8080/v1/chat/completions"),
    "google": ({"id": "gemini", "provider": "google", "model": "gemini-test"}, "GEMINI_API_KEY",
               "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"),
}


@pytest.mark.parametrize("provider", sorted(OTHER))
def test_invoice_program_through_the_real_sdk_of_each_provider(provider, tmp_path, home, monkeypatch):
    """Тот же круг через настоящие SDK openai (с ним — OpenRouter и OpenAI-совместимый сервер) и google-genai, без
    сети: транспорт MockTransport отдаёт записанные ответы в конверте поставщика. Все роли — один оператор. openai 3.x,
    как anthropic 1.x, работает на httpx2, google-genai — на httpx: транспорт и ответ — из библиотеки своего SDK."""
    httpx = pytest.importorskip("httpx" if provider == "google" else "httpx2")
    op, key_env, url = OTHER[provider]
    queue, seen = list(ANSWERS.values()), []

    def server(request):
        seen.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, json=(gemini_response if provider == "google" else chat_completion)(queue.pop(0)))

    transport = httpx.MockTransport(server)
    if provider == "google":
        genai = pytest.importorskip("google.genai")
        real = genai.Client
        monkeypatch.setattr(genai, "Client", lambda **kw: real(**kw, http_options={"httpx_client": httpx.Client(transport=transport)}))
    else:
        openai = pytest.importorskip("openai")
        real = openai.OpenAI
        monkeypatch.setattr(openai, "OpenAI", lambda **kw: real(**kw, http_client=openai.DefaultHttpxClient(transport=transport)))
    if key_env:
        monkeypatch.setenv(key_env, "test-key")
    monkeypatch.delenv("RPTG_KEY_" + op["id"].upper(), raising=False)
    cli.main(["selftest"])
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({k: [{"in": e["in"], "out": e["out"]} for e in v] for k, v in FX["s_new"]["user_examples"].items()},
                                       allow_unicode=True), encoding="utf-8")
    cli.main(["new", str(tmp_path / "app"), "--idea", FX["s_new"]["idea"], "--examples", str(examples)])
    project = store.Project(tmp_path / "app")
    cfg = yaml.safe_load((project.root / "project.yaml").read_text(encoding="utf-8"))
    cfg["operators"] = {op["id"]: presets.op(op["id"], op["provider"], op["model"], prices={"input": "1", "output": "2"},
                                             **({"base_url": op["base_url"]} if "base_url" in op else {}))}
    cfg["roles"] = {role: [op["id"]] for role in ("architect", "designer", "implementer")}
    (project.root / "project.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")

    first = loop.run(project, say=lambda *_: None)
    assert first["kind"] == "ask_user" and first["question"]["approve"] == "app", first
    cli.main(["--project", str(project.root), "approve"])
    assert loop.run(project, say=lambda *_: None) == {"kind": "stop"} and project.load_state()["phase"] == "DONE"
    assert len(seen) == len(ANSWERS) and not queue and {u for u, _ in seen} == {url}
    body = seen[0][1]
    if provider == "google":
        assert body["generationConfig"]["responseMimeType"] == "application/json" and "responseJsonSchema" in body["generationConfig"]
        assert body["systemInstruction"]["parts"][0]["text"]
    else:
        assert body["response_format"]["type"] == "json_schema" and body["response_format"]["json_schema"]["strict"] is False
        assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert float(project.load_state()["budget"]["spent"]) > 0


def test_reading_state_while_it_is_replaced_does_not_fail(tmp_path):
    """08.10: окно читает state.json, пока круг его заменяет (os.replace); на Windows одна из сторон на миг получает
    PermissionError — окно отвечало 500, а круг мог упасть. Чтение и замена переживают столкновение."""
    import threading
    project, errors, stop = store.Project(tmp_path), [], threading.Event()
    project.save_state({"phase": "NEW", "n": 0})

    def reader():
        while not stop.is_set():
            try:
                project.load_state()
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))

    threads = [threading.Thread(target=reader) for _ in range(2)]
    for t in threads:
        t.start()
    try:
        for i in range(400):
            project.save_state({"phase": "NEW", "n": i})
    finally:
        stop.set()
        for t in threads:
            t.join()
    assert errors == [] and project.load_state()["n"] == 399


def test_torn_journal_line_does_not_stop_the_loop(tmp_path):
    project = store.Project(tmp_path)
    project.record({"kind": "command"}, {"journal": [{"kind": "repeat", "subject": "map:app", "data": None}]})
    with open(project.dir / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write('{"at": "2026-10-04T1')
    assert [r.get("kind") for r in project.journal()] == [None, "repeat"]
