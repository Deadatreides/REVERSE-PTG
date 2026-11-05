"""Операторы: смоук (`rptg models test`), калибровка (`rptg models calibrate`), ручное назначение (`rptg assign`).

Модель подменена записанными ответами в конверте Anthropic; ядро, check и песочница — настоящие. Шаблон чата
llama.cpp проверяется на подставной модели: важна логика перехвата промпта, а не веса. Домашняя папка rptg —
временная (RPTG_HOME).

    python -m pytest tests/test_models.py -q
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import designs as design_io  # noqa: E402

from rptg_host import cli, llm, loop, models, store  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.yaml")
FX = {**LOADED.get("shared_fixtures_0", {}), **LOADED.get("fixtures", {})}
ADD = {"name": "add", "doc": "a + b", "params": [{"name": "a", "type": "integer"}, {"name": "b", "type": "integer"}],
       "result": "integer", "requires": [], "ensures": ["result == a + b"], "effects": [],
       "examples": [{**e, "source": "user"} for e in models.PROBE_EXAMPLES["probe:add"]]}
PROBE_MAP = {"map_text": "# Карта probe\n\nОдна операция — сложение двух целых.\n",
             "card": {"id": "probe", "owner": "probe", "purpose": "сумма двух целых", "uses": [], "effects": [], "allowed_imports": [],
                      "est_lines": 3, "ops": [ADD]},
             "types": []}
CODE = {"probe.add": "def add(a: int, b: int) -> int:\n    return a + b\n", "ref.double": "def double(x: int) -> int:\n    return x * 2\n",
        "ref.shout": "def shout(s: str) -> str:\n    return s.upper()\n", "ref.trim": "def trim(s: str) -> str:\n    return s.strip()\n"}
TRIM = {"id": "text-02", "class": "text",
        "card": {"id": "ref.trim", "owner": "ref", "purpose": "строка без пробелов по краям", "uses": [], "effects": [], "allowed_imports": [],
                 "est_lines": 3, "ops": [{"name": "trim", "doc": "без пробелов по краям", "params": [{"name": "s", "type": "string"}],
                                          "result": "string", "requires": [], "ensures": ["len(result) <= len(s)"], "effects": [],
                                          "examples": [{"in": {"s": " ab "}, "out": "ab", "source": "model"}]}]},
        "hidden_tests": {"cases": [{"in": {"s": "  x"}, "out": "x"}]}}


def envelope(content):
    return {"content": [content], "stop_reason": "end_turn", "usage": {"input_tokens": 1000, "output_tokens": 200}}


def fake(calls, wrong=()):
    """Ответы по заданию: карта — вызов инструмента answer, функция — блок python. wrong — пары (узел, оператор),
    у которых функция неверна: у double возвращает вход, у trim подогнана под видимый пример — договор
    len(result) <= len(s) соблюдён, и поймать её может только скрытый случай."""
    def send(task, request, operator):
        calls.append((task["subject"], task["operator"]))
        if task["kind"] == "map":
            return envelope({"type": "tool_use", "id": "t1", "name": "answer", "input": PROBE_MAP})
        node = task["subject"].split(":")[1]
        code = CODE[node].replace("x * 2", "x").replace("s.strip()", '"ab" if s == " ab " else s') if (node, task["operator"]) in wrong \
            else CODE[node]
        return envelope({"type": "text", "text": "```python\n" + code + "```\n"})
    return send


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("RPTG_HOME", str(tmp_path / "home"))
    cli.main(["selftest"])
    return tmp_path / "home"


@pytest.fixture()
def project(tmp_path, home):
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({"app:invoice": [{"in": {"order": {"id": 1, "lines": []}}, "out": {}}]}), encoding="utf-8")
    cli.main(["new", str(tmp_path / "p"), "--idea", "x", "--examples", str(examples)])
    return store.Project(tmp_path / "p")


def core(project):
    return loop.Core(project.config(), project.table())


def test_smoke_passes_on_a_well_formed_operator_and_is_recorded(project, home):
    """Ответ JSON проходит форму П1, функция — Э1, mypy, примеры и скрытые случаи; итог — по отпечатку оператора."""
    calls = []
    report = models.smoke(core(project), "haiku", fake(calls))
    assert report["json"]["form"] == ["pass"] and report["code"]["passed"] and report["passed"]
    assert [kind for kind, _ in calls] == ["map:probe", "function:probe.add:add"] and {op for _, op in calls} == {"haiku"}
    index = json.loads((home / "smoke.json").read_text(encoding="utf-8"))
    assert index[models.fingerprint(project.config()["operators"]["haiku"])]["passed"] is True
    assert len(list((home / "smoke" / f"haiku-{report['fingerprint']}").glob("0*.json"))) == 2        # вызовы — как ушли


def test_smoke_fails_when_the_answer_is_not_strict_json(project, home):
    def broken(task, request, operator):
        if task["kind"] == "map":
            return envelope({"type": "text", "text": "Вот карта: сумма двух чисел."})
        return fake([])(task, request, operator)

    report = models.smoke(core(project), "haiku", broken)
    assert report["json"]["form"] == ["fail"] and not report["passed"]


def test_fingerprint_follows_the_operator_not_its_price():
    op = {"provider": "anthropic", "model": "m", "output_mode": "tool", "steps": "combined", "params": {"max_tokens": 10},
          "prompt_version": "p1", "prices": {"input": "1", "output": "2"}}
    assert models.fingerprint(op) == models.fingerprint({**op, "prices": {"input": "9", "output": "9"}})
    assert models.fingerprint(op) != models.fingerprint({**op, "params": {"max_tokens": 11}})
    assert models.fingerprint(op) != models.fingerprint({**op, "prompt_version": "p2"})


class FakeLlama:
    """Подставная модель llama.cpp: create_chat_completion отдаёт токены промпта в create_completion, как библиотека."""
    def __init__(self, tokens, text, template="{{ messages }}", fmt="chat_template.default"):
        self.metadata = {"tokenizer.chat_template": template, "tokenizer.ggml.bos_token_id": "1", "general.architecture": "gemma3"}
        self.chat_format, self._tokens, self._text = fmt, tokens, text

    def create_chat_completion(self, messages, max_tokens):
        return self.create_completion(prompt=self._tokens, max_tokens=max_tokens)

    def create_completion(self, prompt, **_):
        raise AssertionError("смоук не должен звать модель за промптом")

    def detokenize(self, tokens, special=False):
        assert tokens == self._tokens and special
        return self._text.encode("utf-8")


@pytest.mark.parametrize("tokens, text, answers, template, ok", [
    ([1, 5, 6], "<bos><start_of_turn>user\nYou are the architect in rptg, a program that builds programs as a tree…\n", ["{}"], "t", True),
    ([1, 1, 5], "<bos><bos><start_of_turn>user\nYou are the architect in rptg, a program that builds programs as a tree…\n", ["{}"], "t", False),
    ([1, 5, 6], "<bos><start_of_turn>user\nPlease add the numbers\n", ["{}"], "t", False),
    ([1, 5, 6], "<bos>You are the architect in rptg, a program that builds programs as a tree…", ["{} <start_of_turn>user"], "t", False),
    ([1, 5, 6], "You are the architect in rptg, a program that builds programs as a tree…", ["{}"], "", False),
])
def test_chat_template_check_sees_what_the_model_would_get(monkeypatch, tokens, text, answers, template, ok):
    """MODELS_ONBOARDING §5: двойной BOS, потерянная системная часть, чужой ход в ответе, нет шаблона в GGUF —
    каждое валит смоук; промпт берётся перехватом до модели."""
    llama = FakeLlama(tokens, text, template=template)
    monkeypatch.setattr(llm, "model", lambda payload, op: (llama, dict(payload)))
    system = "You are the architect in rptg, a program that builds programs as a tree of nodes with typed contracts."
    request = {"payload": {"messages": [{"role": "system", "content": system}, {"role": "user", "content": "x"}]}}
    report = models.template({"model": "m.gguf", "params": None}, request, answers)
    assert report["ok"] is ok and report["prompt"] == text and "create_completion" not in llama.__dict__


def reference4():
    """Два рода по две задачи (как b_ref4 у bench): каждый род делится на подбор и проверку поровну; у каждой задачи
    — эталонное решение."""
    double = {**FX["ref_double"], "solution": CODE["ref.double"]}
    trim = {**TRIM, "solution": CODE["ref.trim"]}
    return {"name": "четвёрка", "items": [{**double, "id": "c1"}, {**trim, "id": "t1"}, {**double, "id": "c2"}, {**trim, "id": "t2"}]}


def test_a_task_that_rejects_its_own_reference_stops_the_calibration(project, home):
    """Заготовка ref_shout обещает len(result) == len(s), а s.upper() на «ß» даёт «SS»: свойство (Э3) отвергает
    верное решение — такая задача ничего не меряет (эксп. 2 базы: 60 % наборов тестов отвергли эталон)."""
    models.smoke(core(project), "haiku", fake([]))
    ref = reference4()
    ref["items"][1] = {**FX["ref_shout"], "id": "t1", "solution": CODE["ref.shout"]}
    calls = []
    with pytest.raises(ValueError, match="t1"):
        models.calibrate(core(project), ["haiku"], ref, fake(calls), say=lambda *_: None)
    assert calls == []                                                          # до моделей дело не дошло


def test_calibration_loop_builds_the_table_and_resumes_without_paying_twice(project, home):
    """Каждый оператор на каждой задаче; функция — от ядра, тесты со скрытыми случаями — в песочнице; таблица и G0
    — от competence. Повторный запуск не зовёт модель: пары уже решены тем же оператором."""
    c, calls, said = core(project), [], []
    for op in ("haiku", "sonnet"):
        models.smoke(c, op, fake([]))
    ref = reference4()
    ref["items"][3] = {k: v for k, v in ref["items"][3].items() if k != "solution"}
    table = models.calibrate(c, ["haiku", "sonnet"], ref, fake(calls, wrong={("ref.trim", "haiku")}), say=said.append)
    assert any("t2" in line and "не проверена" in line for line in said)
    assert len(calls) == 8 and table["g0"] is True                     # compute — у haiku дешевле, text — только sonnet
    cells = {(x["class"], x["operator"]): x for x in table["cells"]}
    assert (cells["text", "haiku"]["ok_fit"], cells["text", "haiku"]["ok_check"]) == (0, 0)
    assert (cells["text", "sonnet"]["ok_fit"], cells["text", "sonnet"]["ok_check"]) == (1, 1)
    assert cells["compute", "haiku"]["ok_fit"] == cells["compute", "haiku"]["n_fit"] == 1 and cells["compute", "haiku"]["low_data"]
    assert json.loads((home / "competence.json").read_text(encoding="utf-8")) == table
    rows = store.read_rows(home / "calibration" / "четвёрка" / "results.jsonl")
    assert len(rows) == 8 and all(r["fingerprint"] for r in rows)
    assert models.calibrate(c, ["haiku", "sonnet"], reference4(), fake(calls), say=lambda *_: None) == table and len(calls) == 8

    def down(task, request, operator):
        raise ConnectionError("нет сети")

    with pytest.raises(ConnectionError):
        models.calibrate(c, ["haiku", "sonnet"], reference4(), down, say=lambda *_: None, fresh=True)
    kept = [p for p in (home / "calibration" / "четвёрка").glob("results-*.jsonl")]
    assert len(kept) == 1 and len(store.read_rows(kept[0])) == 8                  # прежние итоги не удалены


def test_calibration_refuses_operators_without_smoke_or_trusted_checks(project, home):
    with pytest.raises(ValueError, match="смоука"):
        models.calibrate(core(project), ["haiku"], reference4(), fake([]), say=lambda *_: None)
    models.smoke(core(project), "haiku", fake([]))
    cfg = {**project.config(), "trusted": ["P1", "E1"]}
    with pytest.raises(ValueError, match="E2, E3"):
        models.calibrate(loop.Core(cfg, project.table()), ["haiku"], reference4(), fake([]), say=lambda *_: None)


def test_unknown_gbnf_escapes_become_hex_and_known_ones_stay():
    assert llm.gbnf(r'a ::= "\." [a\-z] "\"" "\\" [\]] "\x41" "\n"') == r'a ::= "\x2E" [a\x2Dz] "\"" "\\" [\]] "\x41" "\n"'
    assert llm.gbnf("b ::= \"\\Ж\"") == "b ::= \"\\u0416\""


def escapes(text):
    """Экранирования GBNF слева направо, парами: «\\\\» — одна пара."""
    import re
    return {m.group(1) for m in re.finditer(r"\\(.)", text, re.S)}


@pytest.mark.parametrize("task_name", ["task_billing", "task_map"])
def test_answer_schemas_translate_to_a_grammar_llamacpp_can_parse(task_name):
    """Живой смоук 07.10: перевод схемы ответа (шаблон NodeId) давал «\\.», разборщик llama.cpp его не знает, и
    выборка падала. Контрольный случай talk проверял лишь «root ::=» в тексте; здесь — каждое экранирование."""
    grammar = pytest.importorskip("llama_cpp.llama_grammar")
    from test_talk_controls import prompt
    raw = grammar.json_schema_to_gbnf(json.dumps(prompt(task_name, "s_billing").answer_schema))
    assert escapes(raw) - llm.GBNF_ESCAPES                                       # перевод библиотеки — с незнакомыми
    assert not escapes(llm.gbnf(raw)) - llm.GBNF_ESCAPES and llm.gbnf(llm.gbnf(raw)) == llm.gbnf(raw)


@pytest.mark.skipif(not __import__("os").environ.get("RPTG_TEST_GGUF"), reason="путь к любой GGUF — в RPTG_TEST_GGUF")
def test_grammar_is_checked_by_the_llamacpp_parser_before_sampling():
    """На настоящем разборщике: негодная грамматика — исключение, а не нулевой сэмплер; обе схемы ответа после
    перевода разбираются."""
    import os

    from llama_cpp import Llama
    from llama_cpp.llama_grammar import json_schema_to_gbnf
    from test_talk_controls import prompt
    model = Llama(model_path=os.environ["RPTG_TEST_GGUF"], vocab_only=True, verbose=False)
    with pytest.raises(ValueError, match="не разбирается"):
        llm.grammar(model, r'root ::= "\."')
    for name in ("task_billing", "task_map"):
        llm.grammar(model, llm.gbnf(json_schema_to_gbnf(json.dumps(prompt(name, "s_billing").answer_schema))))


def test_models_commands_explain_instead_of_tracing(project, monkeypatch):
    """Неизвестный оператор и нет ключа в окружении — строка с причиной, а не трассировка."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RPTG_KEY_HAIKU", raising=False)
    with pytest.raises(SystemExit, match="нет операторов nobody"):
        cli.main(["--project", str(project.root), "models", "test", "nobody"])
    with pytest.raises(SystemExit, match="прервано: RuntimeError: нет ключа ANTHROPIC_API_KEY"):
        cli.main(["--project", str(project.root), "models", "test", "haiku"])


def test_assign_from_the_command_line(project):
    cli.main(["--project", str(project.root), "assign", "app.billing.**", "--role", "implementer", "--model", "sonnet"])
    cfg = yaml.safe_load((project.root / "project.yaml").read_text(encoding="utf-8"))
    assert cfg["overrides"]["app.billing.**"] == {"implementer": "sonnet"}
    with pytest.raises(SystemExit, match="маска"):
        cli.main(["--project", str(project.root), "assign", "level:2-3", "--role", "implementer", "--model", "sonnet"])
