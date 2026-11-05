"""Контрольные случаи языка условий: заведомо верное, заведомо неверное, неприменимое.

Корпус карты (test_cl_corpus) ловит только ложные отказы: проверка типов, пропускающая всё, его
тоже прошла бы. Здесь — входы, которые обязаны быть отвергнуты, с частью текста причины, и
тонкие верные случаи (проверка на null в посылке, в «или», переменная квантора). Ожидания
написаны по LOGIC §4, а не подогнаны под вывод листов.

    python -m pytest tests/test_lang_controls.py -q
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rptg._types import EvalResult, Limits, TypeEnv  # noqa: E402
from rptg.lang.cl.evaluate import evaluate  # noqa: E402
from rptg.lang.cl.logic.schema import facts  # noqa: E402
from rptg.lang.cl.logic.smt import term  # noqa: E402
from rptg.lang.cl.parse import parse  # noqa: E402
from rptg.lang.cl.python import python  # noqa: E402
from rptg.lang.cl.typecheck import typecheck  # noqa: E402

DECIMAL = {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}
TYPES = {
    "Decimal": DECIMAL,
    "Json": {},
    "Mode": {"type": "string", "enum": ["A", "B"]},
    "Line": {"type": "object", "required": ["qty", "price"], "properties": {
        "qty": {"type": "integer"}, "price": {"$ref": "Decimal"}, "note": {"type": "string"}}},
    "Rec": {"type": "object", "required": ["n", "lines", "mode", "tags", "meta"], "properties": {
        "n": {"type": "integer"}, "opt": {"type": "integer", "minimum": 1},
        "lines": {"type": "array", "items": {"$ref": "Line"}}, "mode": {"$ref": "Mode"},
        "tags": {"type": "object", "additionalProperties": {"type": "string"}}, "meta": {"$ref": "Json"},
        "ratio": {"type": "number"}, "sub": {"$ref": "Line"}, "in": {"type": "integer"}}},
}
ENV = TypeEnv(types=TYPES, vars={"r": "Rec", "s": "string", "x": "integer", "d": "Decimal", "xs": "[integer]",
                                 "i": "integer"})
LIMITS = Limits(max_depth=8, max_children=7, final_max_ops=6, final_max_lines=40, max_complexity=10,
                k_lists=3, z3_rlimit=5000000, hypothesis_examples=200)


def typed(text):
    return typecheck(parse(text), ENV)


GOOD = [
    "r.n > 0",
    "r.opt != null and r.opt > 0",
    "r.opt != null => r.opt > 0",
    "r.opt == null or r.opt > 0",
    "not (r.opt == null) and r.opt > 0",
    "forall l in r.lines: l.qty > 0 and l.price >= 0",
    "sum(l.qty for l in r.lines) >= 0",
    "count(l.qty > 1 for l in r.lines) <= len(r.lines)",
    'r.mode == "A"',
    'r.mode in {"A", "B"}',
    '"k" in r.tags',
    "len(r.tags) >= 0",
    "r.meta != null",
    "r.sub != null and r.sub.note != null => len(r.sub.note) > 0",
    "r.lines[0].qty > 0",
    "d > 0.5",
    "x % 2 == 0",
    'startswith(s, "a")',
    "r.ratio != null => r.ratio > 0.5",
    "abs(x) >= 0 and min(x, 3) <= 3",
    "forall class in r.lines: class.qty > 0",
    "r.in != null",
]

BAD = [
    ("r.opt > 0", "может быть null"),
    ("r.opt > 0 and r.opt != null", "может быть null"),
    ('r.mode == "C"', "не из перечисления"),
    ('r.mode in {"A", "C"}', "не из перечисления"),
    ('s < "a"', "порядок"),
    ("d % 2 == 0", "только у целых"),
    ("r.ratio != null and r.ratio + d > 0", "смешаны decimal и number"),
    ("r.meta.x > 0", "не у записи"),
    ('r.tags.k == "v"', "не у записи"),
    ('r.tags[0] == "v"', "не у списка"),
    ("y > 0", "не объявлено"),
    ("result > 0", "не объявлено"),
    ("forall c in s: true", "по списку"),
    ("r.n != null", "не бывает null"),
    ("r.lines[s].qty > 0", "индекс не целый"),
    ("x + 1", "не логическое"),
    ("r.lines > 0", "только у чисел"),
    ("r.n == r.mode", "разные виды"),
    ("sum(l.qty > 0 for l in r.lines) > 0", "sum — по числам"),
    ("len(x) > 0", "len"),
    ("r.nope > 0", "нет поля"),
]


@pytest.mark.parametrize("text", GOOD)
def test_good_conditions_typecheck(text):
    t = typed(text)
    assert t.ok, t.errors


@pytest.mark.parametrize("text, why", BAD)
def test_bad_conditions_are_rejected(text, why):
    t = typed(text)
    assert not t.ok, f"«{text}» принято, а должно быть отвергнуто"
    assert any(why in e for e in t.errors), t.errors


@pytest.mark.parametrize("text", ["x >", "(x > 0", "x > 0)", "forall in in xs: true", '"a\\q" == s', "x ! 0", ""])
def test_bad_text_does_not_parse(text):
    p = parse(text)
    assert not p.ok and p.errors and "позиция" in p.errors[0]


def test_field_after_dot_may_be_a_keyword():
    assert parse("example.in != null and result.class == 1").ok


def test_unparsed_input_is_not_typed():
    t = typecheck(parse("x >"), ENV)
    assert not t.ok and t.errors


VALUES = {"r": {"n": 2, "lines": [{"qty": 2, "price": "1.50"}], "mode": "A", "tags": {"k": "v"}, "meta": None},
          "s": "ab", "x": 1, "d": "2.50", "xs": [1, 2], "i": 0}


@pytest.mark.parametrize("text, want", [
    ("x / 0 > 1", EvalResult(ok=True, value=False)),
    ("d > 1", EvalResult(ok=True, value=True)),
    ("0.1 + 0.2 == 0.3", EvalResult(ok=True, value=True)),
    ("r.opt != null and r.opt > 0", EvalResult(ok=True, value=False)),
    ("r.opt == null or r.opt > 100", EvalResult(ok=True, value=True)),
    ("forall l in r.lines: l.price > 1", EvalResult(ok=True, value=True)),
    ("sum(l.qty for l in r.lines) == 2", EvalResult(ok=True, value=True)),
    ('"k" in r.tags and r.mode in {"A"}', EvalResult(ok=True, value=True)),
])
def test_evaluate_values(text, want):
    assert evaluate(typed(text), VALUES) == want


def test_evaluate_index_out_of_range_is_an_error_not_a_verdict():
    got = evaluate(typed("r.lines[5].qty > 0"), VALUES)
    assert not got.ok and got.error


@pytest.mark.parametrize("text, want", [
    ("r.in != null", "(r.in_ is not None)"),
    ("d > 1", "(Decimal(d) > 1)"),
    ("forall class in r.lines: class.qty > 0", "all((class_.qty > 0) for class_ in r.lines)"),
    ("r.opt == null or r.opt > 0", "((r.opt is None) or (r.opt > 0))"),
    ('r.mode in {"A", "B"}', '(r.mode in ("A", "B",))'),
    ("count(l.qty > 1 for l in r.lines) >= 0", "(sum(1 for l in r.lines if (l.qty > 1)) >= 0)"),
])
def test_python_text(text, want):
    assert python(typed(text)) == want


def smt(text):
    return facts(term(typed(text), LIMITS), ENV, LIMITS)


def test_smt_exists_is_a_bounded_disjunction():
    got = smt("exists v in xs: v > 0")
    assert got.term == ("(or (and (> |len(xs)| 0) (> |xs[0]| 0)) (and (> |len(xs)| 1) (> |xs[1]| 0)) "
                        "(and (> |len(xs)| 2) (> |xs[2]| 0)))")
    assert got.facts == ["(<= 0 |len(xs)| 3)"]


def test_smt_optional_value_is_guarded_by_presence():
    got = smt("r.opt != null => r.opt > 0")
    assert got.term == "(=> |r.opt?| (> |r.opt| 0))"
    assert got.sorts == {"r.opt?": "Bool", "r.opt": "Int"}
    assert got.facts == ["(=> |r.opt?| (<= 1 |r.opt|))"]


def test_smt_string_literal_is_escaped():
    assert smt('s == "ё\\""').term == '(= |s| "\\u{451}""")'


def test_smt_variable_index_is_defined_only_inside_the_list():
    got = smt("xs[i] > 0")
    assert got.term.startswith("(and (and (<= 0 |i|) (< |i| |len(xs)|)) (> (ite (= |i| 0) |xs[0]| (ite (= |i| 1) |xs[1]|")


def test_smt_division_by_zero_makes_the_condition_false():
    got = smt("r.n / x > 1")
    assert got.term == "(and (not (= |x| 0)) (> (/ (to_real |r.n|) (to_real |x|)) 1.0))"


def test_smt_short_circuit_guard_keeps_division_defined():
    # x != 0 => r.n / x > 1: при x = 0 посылка ложна, деление не вычисляется — условие истинно
    got = smt("x != 0 => r.n / x > 1")
    assert got.term == ("(and (=> (not (= |x| 0)) (not (= |x| 0))) "
                        "(=> (not (= |x| 0)) (> (/ (to_real |r.n|) (to_real |x|)) 1.0)))")


def test_subtype_terminates_on_alias_ring():
    # A → B → A без структуры: договор sub требует ответа, а не зацикливания; ответ — «не доказано»
    from rptg.lang.types import sub
    ring = TypeEnv(types={"A": {"$ref": "B"}, "B": {"$ref": "A"}, "C": {"type": "integer"}}, vars={})
    assert not sub("A", "C", ring).ok
    assert sub("A", "A", ring).ok


def test_smt_refuses_dictionary_membership_instead_of_guessing():
    got = smt('"k" in r.tags')
    assert not got.ok and "словарь" in got.errors[0]


# ── границы стратегий (30.09.2026, постройка build): путь, forall, строгость по виду пути ──
# Граница сужает порождение, поэтому обязана следовать из условия: иначе свойство молча не увидит
# годных входов. Ожидания — по LOGIC §4: индекс говорит об одном элементе, exists — об одном из,
# «или» и импликация — не о каждом входе; строгое «>» у нецелого не сдвигает границу на 1.

BOUNDS = [
    ("r.n > 0 and r.n > 3", [("r.n", "value", "min", 4)]),
    ("len(r.lines) >= 1", [("r.lines", "size", "min", 1)]),
    ("forall l in r.lines: l.qty > 0 and l.price >= 0",
     [("r.lines[].price", "value", "min", 0), ("r.lines[].qty", "value", "min", 1)]),
    ("r.opt != null and r.opt > 0", [("r.opt", "value", "min", 1)]),
    ("r.ratio != null and r.ratio > 0", [("r.ratio", "value", "min", 0)]),
    ("d > 0 and d < 3", [("d", "value", "min", 0), ("d", "value", "max", 3)]),
    ("forall x in xs: x < 10", [("xs[]", "value", "max", 9)]),
    ("len(s) < 5 and 2 < x", [("s", "size", "max", 4), ("x", "value", "min", 3)]),
    ("r.lines[0].qty > 0", []),
    ("forall l in r.lines: l.qty > r.n", []),
    ("exists l in r.lines: l.qty > 3", []),
    ("r.ratio != null => r.ratio > 0", []),
    ("r.n > 0 or r.n < -5", []),
]


@pytest.mark.parametrize("text, want", BOUNDS)
def test_bounds_by_path(text, want):
    from rptg.lang.cl.strategy.bounds import bounds
    assert [(b.name, b.what, b.side, b.v) for b in bounds([typed(text)])] == want


@pytest.mark.parametrize("text", [t for t, want in BOUNDS if want])
def test_bound_holds_on_every_input_the_condition_accepts(text):
    """Граница — следствие условия: входы порождает стратегия без границ, фильтр — само условие
    (evaluate); на каждом принятом входе каждое значение по пути границы лежит в ней."""
    from decimal import Decimal

    from hypothesis import HealthCheck, assume, given, settings, strategies as st

    from rptg._types import Param
    from rptg.lang.cl.strategy.bounds import bounds
    from rptg.lang.cl.strategy.gen import gen

    t, free = typed(text), gen([Param(name=n, type=tp) for n, tp in ENV.vars.items()], [], ENV)
    found = bounds([t])

    def at(values, path):
        out = [values]
        for part in path.replace("[]", ".[]").split("."):
            out = [y for v in out for y in (v if part == "[]" else [v.get(part)] if isinstance(v, dict) else [])]
        return [v for v in out if v is not None]

    @settings(max_examples=300, derandomize=True, database=None, suppress_health_check=list(HealthCheck))
    @given(st.fixed_dictionaries({n: eval(s, {"st": st}) for n, s in free.items()}))
    def prop(values):
        got = evaluate(t, values)
        assume(got.ok and got.value is True)
        for b in found:
            for v in at(values, b.name):
                size = len(v) if b.what == "size" else Decimal(str(v))
                assert (size >= b.v) if b.side == "min" else (size <= b.v), (b, v)

    prop()


def test_gen_applies_a_bound_only_at_its_path():
    """r.n и n — разные места: граница параметра не ложится на одноимённое поле записи."""
    from rptg._types import Param
    from rptg.lang.cl.strategy._types import Bound
    from rptg.lang.cl.strategy.gen import gen

    got = gen([Param(name="r", type="Rec")], [Bound(name="n", what="value", side="min", v=5),
                                             Bound(name="r.lines", what="size", side="min", v=1),
                                             Bound(name="r.lines[].qty", what="value", side="min", v=1)], ENV)["r"]
    assert '"n": st.integers()' in got
    assert 'st.lists(elements=st.fixed_dictionaries({"qty": st.integers(min_value=1)' in got and "min_size=1)" in got
