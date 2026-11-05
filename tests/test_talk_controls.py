"""Контрольные случаи rptg.talk (LOGIC §8, ARCHITECTURE §5; правила базы — CONTEXT_MODEL §4 и §6,
experiment13, experiment14, MODEL_INTERFACE §2).

Случаи написаны по правилам, а не подогнаны под вывод листов: провал случая — дефект talk.
Главные — сквозные: схема ответа из подсказки совпадает со схемой П1; ответ, который модель дала
по этой схеме через любой протокол, проходит разбор конверта и П1 проверок; схема переводится в
грамматику llama.cpp без отката к «любому JSON».

    python -m pytest tests/test_talk_controls.py -q
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402

from rptg import _types as T  # noqa: E402
from rptg._values import dump, load  # noqa: E402
from rptg.talk import _types as TT  # noqa: E402

import rptg.talk as talk  # noqa: E402

LOADED = design_io.load(ROOT / "design" / "rptg.talk.context.yaml")
FX = {**LOADED["shared_fixtures_0"], **LOADED["shared_fixtures_1"], **LOADED["fixtures"]}
CFG = load(T.Config, FX["cfg"])
CFG_TALK = load(T.Config, FX["cfg_talk"])


def task(name, **changes):
    return load(T.Task, {**FX[name], **changes})


def state(name):
    return load(T.State, FX[name])


def prompt(task_name, state_name, cfg=CFG, **changes):
    return talk.prompt(task=task(task_name, **changes), state=state(state_name), cfg=cfg)


def paragraphs(text):
    return text.split("\n\n")


def unref(schema):
    """Ссылки #/$defs/Имя → Имя: запись ядра."""
    if isinstance(schema, list):
        return [unref(v) for v in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: unref(v) for k, v in schema.items()}
    if isinstance(out.get("$ref"), str):
        out["$ref"] = out["$ref"].removeprefix("#/$defs/")
    return out


# ── схема ответа = схема П1 ─────────────────────────────────────────────────

def p1_types():
    """Закрытые схемы, по которым П1 проверяет ответ (check.answer.shape)."""
    from rptg._types import Answer
    from rptg.check.answer import shape
    jobs = shape.jobs(state={}, answer=Answer(ok=True, kind="design", subject="design:app", node="app", truncated=False,
                                              value={}))
    return jobs[0].env.types


@pytest.mark.parametrize("task_name, root", [("task_billing", "Design"), ("task_map", "MapAnswer")])
def test_answer_schema_is_p1_schema(task_name, root):
    schema = copy.deepcopy(prompt(task_name, "s_billing").answer_schema)
    defs = unref(schema.pop("$defs"))
    closed = p1_types()
    assert unref(schema) == closed[root]
    for name, sub in defs.items():
        assert sub == closed[name], name


def validator(schema):
    return jsonschema.Draft202012Validator(schema)


MAP_VALUE = {"map_text": "# Карта app\n", "card": FX["c_app"], "types": [FX["t_money"], FX["t_line"], FX["t_order"], FX["t_invoice"]]}


@pytest.mark.parametrize("task_name, value", [
    ("task_billing", FX["d_billing"]),
    ("task_billing", FX["d_app"]),
    ("task_map", MAP_VALUE),
])
def test_schema_accepts_valid_answers(task_name, value):
    assert not list(validator(prompt(task_name, "s_billing").answer_schema).iter_errors(value))


def bad(value, path, key, new):
    v = copy.deepcopy(value)
    target = v
    for p in path:
        target = target[p]
    if new is None:
        del target[key]
    else:
        target[key] = new
    return v


@pytest.mark.parametrize("task_name, value", [
    ("task_billing", bad(FX["d_billing"], ["children", 0], "comment", "лишний ключ")),
    ("task_billing", bad(FX["d_billing"], [], "flows", None)),
    ("task_billing", bad(FX["d_billing"], ["flows", "make_invoice", "nodes", 0], "note", "лишний ключ в узле схемы")),
    ("task_map", bad(MAP_VALUE, ["card"], "est_lines", "восемьдесят")),
])
def test_schema_rejects_invalid_answers(task_name, value):
    assert list(validator(prompt(task_name, "s_billing").answer_schema).iter_errors(value))


@pytest.mark.parametrize("task_name", ["task_billing", "task_map"])
def test_schema_converts_to_llamacpp_grammar(task_name):
    """llama-cpp-python при неудаче перевода молча берёт «любой JSON» — перевод обязан проходить."""
    grammar = pytest.importorskip("llama_cpp.llama_grammar")
    gbnf = grammar.json_schema_to_gbnf(json.dumps(prompt(task_name, "s_billing").answer_schema))
    assert "root ::=" in gbnf
    with pytest.raises(ValueError):  # запись ядра {$ref: Имя} перевод бы не принял
        grammar.json_schema_to_gbnf(json.dumps(unref(prompt(task_name, "s_billing").answer_schema)))


def test_function_has_no_answer_schema():
    p = prompt("task_gguf", "s_build")
    assert p.answer_schema is None
    assert "```python" in p.prefix and "The answer schema:" not in p.prefix


# ── правило контекста: только перечисленное (LOGIC §8.1, F35) ──────────────

TITLES = FX["texts_p1"]["titles"]


def shown(body):
    return {k for k, title in TITLES.items() if f"## {title}\n" in body}


def test_map_sees_idea_and_examples_only():
    body = prompt("task_map", "s_new").body
    assert shown(body) == {"idea", "examples"}
    assert "накладные по заказам" in body


def test_implementer_does_not_see_the_tree():
    body = prompt("task_gguf", "s_build").body
    assert shown(body) == {"op", "purpose", "types", "imports", "limits"}
    assert "накладные по заказам" not in body          # назначение корня
    assert "make_invoice" not in body                  # операция родителя


def test_designer_sees_interfaces_of_uses_only():
    body = prompt("task_billing", "s_billing").body
    assert shown(body) == {"card", "path", "uses", "types", "limits"}   # раздела карты у ветви нет
    assert "\"add\"" in body
    assert "денежные суммы" not in body                # назначение узла из uses — не интерфейс
    assert "\"3.50\"" not in body                      # примеры операций uses не показываются


def test_revision_sees_its_design_and_reports_below():
    body = prompt("task_rev", "s_rev").body
    assert {"design", "below"} <= shown(body)
    assert "функция не выполнила пример" in body


def test_previous_answer_has_no_section():
    """F1: ключа для прежнего ответа нет — раздел с ним не пройдёт тип Fact."""
    schema = json.loads(json.dumps(TT.SCHEMAS["Fact"]).replace('"$ref": "Json"', '"$ref": "#/$defs/Json"'))
    fact = validator({**schema, "$defs": {"Json": {}}})
    assert not list(fact.iter_errors({"key": "report", "value": {}}))
    assert list(fact.iter_errors({"key": "answer", "value": "прежний ответ"}))


# ── устойчивый префикс и формулировки (experiment13, кэш) ──────────────────

def test_prefix_is_stable_across_wording_and_repair():
    primary = prompt("task_billing", "s_billing")
    alternative = prompt("task_alt", "s_billing")
    repair = prompt("task_repair", "s_billing")
    assert primary.prefix == alternative.prefix == repair.prefix
    assert primary.cache_key == alternative.cache_key == repair.cache_key
    assert len({primary.body, alternative.body, repair.body}) == 3


def test_alternative_wording_changes_only_the_instruction():
    primary = paragraphs(prompt("task_billing", "s_billing").body)
    alternative = paragraphs(prompt("task_alt", "s_billing").body)
    assert primary[0] != alternative[0]
    assert alternative[1] == FX["texts_p1"]["form"]
    assert alternative[2:] == primary[1:]


def test_repair_puts_report_first_and_keeps_facts():
    """Отчёт — сразу после указания задачи: K1 измерил монотонный распад полноты по позиции."""
    primary = paragraphs(prompt("task_billing", "s_billing").body)
    repair = paragraphs(prompt("task_repair", "s_billing").body)
    lines = FX["texts_p1"]["repair"]
    assert repair[0] == primary[0]
    assert repair[1].startswith(f"## {TITLES['report']}\n")
    assert "a.currency == b.currency" in repair[1] and "\"EUR\"" in repair[1]
    assert repair[2:2 + len(lines)] == lines
    assert repair[2 + len(lines):] == primary[1:]


def test_same_role_same_kind_same_prefix():
    a = prompt("task_billing", "s_build")
    b = prompt("task_billing", "s_build", subject="design:app.money")
    assert a.prefix == b.prefix and a.body != b.body


def cfg_with(provider, output_mode, version="p1"):
    raw = copy.deepcopy(FX["cfg"])
    raw["operators"]["x"] = {"id": "x", "provider": provider, "model": "m", "base_url": "http://127.0.0.1:1/v1",
                             "output_mode": output_mode, "steps": "combined", "prices": {"input": "0", "output": "0"},
                             "prompt_version": version}
    return load(T.Config, raw)


def test_no_prompt_for_a_version_without_texts():
    """Версия — часть идентичности оператора: подсказку чужой версии под своей меткой не собрать."""
    t = task("task_billing", operator="x")
    with pytest.raises(KeyError):
        talk.prompt(task=t, state=state("s_billing"), cfg=cfg_with("google", "json_schema", version="p9"))


# ── запрос: способ вывода и протокол ───────────────────────────────────────

KINDS = ["map", "design", "revision", "function"]
MODES = ["json_schema", "tool", "grammar", "prompt"]
# что поставщик умеет для ответов rptg (ARCHITECTURE §5.1 после находки talk): строгий
# структурный вывод Anthropic не вмещает словарей и непрозрачного JSON
CAN = {"anthropic": {"tool", "prompt"}, "openai": {"json_schema", "tool", "prompt"},
       "openrouter": {"json_schema", "tool", "prompt"}, "openai_compatible": {"json_schema", "tool", "prompt"},
       "google": {"json_schema", "prompt"}, "llamacpp": {"grammar", "json_schema", "prompt"}}


@pytest.mark.parametrize("provider", sorted(CAN))
@pytest.mark.parametrize("output_mode", MODES)
@pytest.mark.parametrize("kind", KINDS)
def test_mode_is_what_the_provider_can(provider, output_mode, kind):
    subject = "function:app.billing.lines:line_total" if kind == "function" else "design:app.billing"
    t = load(T.Task, {"subject": subject, "kind": kind, "role": "designer", "operator": "x", "attempt": 1, "wording": "primary"})
    cfg = cfg_with(provider, output_mode)
    r = talk.request(prompt=talk.prompt(task=t, state=state("s_rev"), cfg=cfg), task=t, cfg=cfg)
    assert r.mode in CAN[provider]
    if kind == "function":
        assert r.mode == ("grammar" if provider == "llamacpp" and output_mode == "grammar" else "prompt")
    elif output_mode in CAN[provider]:
        assert r.mode == output_mode
    if provider == "anthropic":
        assert r.payload["system"][0]["cache_control"] == {"type": "ephemeral"}


def keys(value):
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


@pytest.mark.parametrize("operator", ["opus", "gemini", "grok", "mini", "gguf", "gpt", "local", "claude_p"])
def test_request_carries_prompt_schema_and_no_keys(operator):
    t = task("task_billing", operator=operator)
    p = talk.prompt(task=t, state=state("s_billing"), cfg=CFG_TALK)
    r = talk.request(prompt=p, task=t, cfg=CFG_TALK)
    assert json.dumps(p.prefix, ensure_ascii=False) in json.dumps(r.payload, ensure_ascii=False)
    assert json.dumps(p.body, ensure_ascii=False) in json.dumps(r.payload, ensure_ascii=False)
    assert not keys(r.payload) & {"api_key", "key", "authorization", "x-api-key", "x-goog-api-key"}
    if r.mode in ("tool", "json_schema"):
        assert json.dumps(p.answer_schema, sort_keys=True) in json.dumps(r.payload, sort_keys=True)


# ── сквозной путь: запрос → ответ поставщика → разбор → П1 ─────────────────

HAS_Z3 = importlib.util.find_spec("z3") is not None
needs_z3 = pytest.mark.skipif(not HAS_Z3, reason="конвейер проверок доходит до решателя, а z3-solver не установлен")


def evaluate(state_name, task_name, answer):
    import rptg.check as check
    event = {"kind": "model_answered", "task": FX[task_name], "answer": dump(answer)}
    return check.evaluate(state=state(state_name), event=load(T.Event, event), cfg=CFG)


def p1(state_name, task_name, answer):
    return next(e.verdict for e in evaluate(state_name, task_name, answer) if e.check == "P1")


def anthropic_tool(value):
    return {"id": "msg_9", "type": "message", "role": "assistant", "stop_reason": "tool_use",
            "content": [{"type": "text", "text": "Готово."}, {"type": "tool_use", "id": "toolu_9", "name": "answer", "input": value}],
            "usage": {"input_tokens": 900, "output_tokens": 700, "cache_read_input_tokens": None, "cache_creation_input_tokens": None}}


def google_json(value):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(value, ensure_ascii=False)}]},
                            "finishReason": "STOP"}], "usageMetadata": {"promptTokenCount": 5000, "candidatesTokenCount": 900}}


@needs_z3
@pytest.mark.parametrize("value, verdict", [(MAP_VALUE, "pass"), (bad(MAP_VALUE, [], "comment", "лишнее"), "fail")])
def test_map_answer_via_anthropic_tool_meets_p1(value, verdict):
    p = prompt("task_map", "s_map")
    r = talk.request(prompt=p, task=task("task_map"), cfg=CFG)
    assert r.mode == "tool" and r.payload["tools"][0]["input_schema"] == p.answer_schema
    schema_ok = not list(validator(p.answer_schema).iter_errors(value))
    answer = talk.response(provider="anthropic", raw=anthropic_tool(value))
    assert answer.input_tokens == 900 and answer.cache_read_tokens == 0
    assert p1("s_map", "task_map", answer) == verdict
    assert schema_ok == (verdict == "pass")


@needs_z3
@pytest.mark.parametrize("value, verdict", [
    ({k: v for k, v in FX["d_billing"].items() if k != "node"}, "pass"),
    (bad(FX["d_billing"], ["children", 0], "comment", "лишнее"), "fail"),
])
def test_design_answer_via_google_json_meets_p1(value, verdict):
    answer = talk.response(provider="google", raw=google_json(value))
    assert p1("s_billing", "task_billing", answer) == verdict


@needs_z3
def test_function_answer_via_llamacpp_grammar_meets_e1():
    t = task("task_gguf")
    r = talk.request(prompt=prompt("task_gguf", "s_build"), task=t, cfg=CFG)
    assert r.mode == "grammar" and r.payload["grammar"].startswith('root ::= "```python')
    raw = {"choices": [{"index": 0, "message": {"role": "assistant", "content": "```python\n" + FX["code_lt"] + "```"},
                        "finish_reason": "stop"}], "usage": {"prompt_tokens": 800, "completion_tokens": 60}}
    answer = talk.response(provider="llamacpp", raw=raw)
    assert [e.verdict for e in evaluate("s_build", "task_gguf", answer) if e.check == "E1"] == ["pass"]


# ── разбор конверта: края ──────────────────────────────────────────────────

def test_anthropic_nulls_and_first_tool_call():
    raw = anthropic_tool({"a": 1})
    raw["content"].append({"type": "tool_use", "id": "toolu_10", "name": "answer", "input": {"b": 2}})
    a = talk.response(provider="anthropic", raw=raw)
    assert a.text == '{"a": 1}' and a.cache_read_tokens == 0 and a.finish_reason == "tool_use"


def test_truncation_passes_through_for_check():
    a = talk.response(provider="anthropic", raw={**anthropic_tool({"a": 1}), "stop_reason": "max_tokens"})
    g = talk.response(provider="google", raw={**google_json({}), "candidates": [{"content": {"parts": [{"text": "{"}]}, "finishReason": "MAX_TOKENS"}]})
    assert a.finish_reason == "max_tokens" and g.finish_reason.lower() == "max_tokens"


def test_chat_without_usage_or_choices():
    a = talk.response(provider="openai_compatible", raw={"choices": [], "usage": None})
    assert (a.text, a.input_tokens, a.output_tokens, a.refusal) == ("", 0, 0, False)
    f = talk.response(provider="openai", raw={"choices": [{"message": {"content": None}, "finish_reason": "content_filter"}]})
    assert f.refusal and f.finish_reason == "refusal"


def test_chat_cached_tokens_are_not_billed_as_input():
    raw = {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
           "usage": {"prompt_tokens": 1500, "completion_tokens": 3, "prompt_tokens_details": {"cached_tokens": 1024}}}
    a = talk.response(provider="openai", raw=raw)
    assert (a.input_tokens, a.cache_read_tokens) == (476, 1024)


def test_google_thoughts_are_paid_but_are_not_the_answer():
    raw = {"candidates": [{"content": {"parts": [{"text": "думаю", "thought": True}, {"text": "{}"}]}, "finishReason": "STOP"}],
           "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2, "thoughtsTokenCount": 30}}
    a = talk.response(provider="google", raw=raw)
    assert (a.text, a.output_tokens) == ("{}", 32)


def test_google_function_call_and_bogus_cache_count():
    raw = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "answer", "args": {"ok": 1}}}]}, "finishReason": "STOP"}],
           "usageMetadata": {"promptTokenCount": 10, "cachedContentTokenCount": 50, "candidatesTokenCount": 5}}
    a = talk.response(provider="google", raw=raw)
    assert a.text == '{"ok": 1}' and a.input_tokens == 0 and a.cache_read_tokens == 50


# ── цена: точная десятичная ────────────────────────────────────────────────

def op_priced(**prices):
    return load(T.Operator, {"id": "p", "provider": "openai", "model": "m", "output_mode": "prompt", "steps": "combined",
                             "prices": prices, "prompt_version": "p1"})


def raw_answer(i, o, c=0):
    return load(T.RawAnswer, {"text": "", "input_tokens": i, "output_tokens": o, "cache_read_tokens": c,
                              "finish_reason": "stop", "refusal": False})


@pytest.mark.parametrize("answer, prices, out", [
    (raw_answer(1, 0), {"input": "0.000001", "output": "0"}, "0.000000000001"),
    (raw_answer(10 ** 9, 0), {"input": "15", "output": "0"}, "15000"),
    (raw_answer(0, 0, 1000), {"input": "3", "output": "15"}, "0.003"),
    (raw_answer(0, 0, 1000), {"input": "3", "output": "15", "cache": "0.30"}, "0.0003"),
    (raw_answer(333, 333), {"input": "0.1", "output": "0.2"}, "0.0000999"),
])
def test_cost_is_exact(answer, prices, out):
    assert talk.cost(answer=answer, operator=op_priced(**prices)) == out


# ── тексты версии p1 полны ─────────────────────────────────────────────────

def test_texts_are_complete():
    texts = load(TT.PromptTexts, FX["prompt_texts"])
    assert set(texts) == {"p1"}
    assert set(TITLES) == set(TT.SCHEMAS["Fact"]["properties"]["key"]["enum"])
