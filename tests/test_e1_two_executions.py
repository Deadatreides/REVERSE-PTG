"""Два исполнения Э1: статика в продукте (rptg.check.code:static) и затравка tools/leafcheck0.py.

Каждая функция каждого листа rptg подаётся продукту как ответ модели на задачу «Ф функция»: строка
документации модуля, его импорты, блок TYPE_CHECKING и одно определение — так, как функцию пишет
исполнитель. Затравка проверяет модуль целиком. Вердикт по функции обязан совпасть: расхождение —
дефект одного из исполнений (урок arch1: строгость проверки не означает её правильности, F10).

    python -m pytest tests/test_e1_two_executions.py -q
"""
import ast
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import designs as design_io  # noqa: E402
import leafcheck0 as lc  # noqa: E402

pytest.importorskip("radon")

from rptg import _types as T  # noqa: E402
from rptg._values import load  # noqa: E402
from rptg._types import Answer  # noqa: E402

import rptg.check.code as code  # noqa: E402

PROJECT = yaml.safe_load((ROOT / "design" / "project.yaml").read_text(encoding="utf-8"))
CFG = load(T.Config, {k: PROJECT[k] for k in ("limits", "roles", "operators", "routing", "repair", "overrides", "contracts")})


def leaves():
    designs = [d for _, d in design_io.designs()]
    composite = {d["node"] for d in designs}
    for d in designs:
        for card in d["children"]:
            path = ROOT.joinpath(*card["id"].split(".")).with_suffix(".py")
            if card["id"] not in composite and path.exists():
                for op in card["ops"]:
                    yield card, op["name"], path


def single(path, name):
    """Модуль из одной функции: документация, импорты, TYPE_CHECKING и def name — строками исходника."""
    text = path.read_text(encoding="utf-8")
    lines, keep = text.splitlines(), []
    for i, s in enumerate(ast.parse(text).body):
        doc = i == 0 and isinstance(s, ast.Expr)
        head = isinstance(s, (ast.Import, ast.ImportFrom)) or (isinstance(s, ast.If) and ast.unparse(s.test) == "TYPE_CHECKING")
        if doc or head or (isinstance(s, ast.FunctionDef) and s.name == name):
            keep += lines[s.lineno - 1:s.end_lineno] + [""]
    return "\n".join(keep) + "\n"


CASES = sorted(leaves(), key=lambda c: (c[0]["id"], c[1]))


@pytest.mark.parametrize("card, name, path", CASES, ids=[f"{c[0]['id']}:{c[1]}" for c in CASES])
def test_product_e1_agrees_with_bootstrap(card, name, path):
    own = {k.split(":", 1)[1]: v for k, v in PROJECT["contracts"].items() if k.split(":", 1)[0] == card["id"]}
    problems, _, _ = lc.check_leaf(card, path, PROJECT["limits"], PROJECT["overrides"].get(card["id"], {}), own)
    bootstrap = [p for p in problems if p.startswith(f"{name}:")]
    answer = Answer(ok=True, kind="function", subject=f"function:{card['id']}:{name}", node=card["id"], op=name,
                    code=single(path, name), truncated=False)
    evidence = code.static({"cards": {card["id"]: card}}, answer, CFG)
    product = evidence[0].details.get("problems", []) if evidence[0].verdict == "fail" else []
    assert (evidence[0].verdict == "pass") == (not bootstrap), f"продукт: {product}\nзатравка: {bootstrap}"
    assert sorted(product) == sorted(bootstrap)


def test_every_leaf_function_is_covered():
    assert len(CASES) >= 45
