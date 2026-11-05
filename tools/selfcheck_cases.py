"""Контрольные случаи прототипа проверок tools/selfcheck.py.

Три вида, как в arch1 (WORK_PLAN, этап 3): заведомо верный вход, заведомо неверный вход,
неприменимый вход; плюс сбой самой проверки (ERROR, не нарушение — arch0 SEAM_MODEL §4).
Случаи написаны по документированному правилу, а не подогнаны под вывод прототипа:
провал случая означает дефект проверки, а не повод поправить ожидание (SEAM_MODEL §5.3).

    python tools/selfcheck_cases.py
"""
import contextlib
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import selfcheck as sc  # noqa: E402

# (имя, файл, образец, замена, что обязано быть в отчёте)
BAD = [
    ("П7 ложная гарантия", "rptg.yaml", "out: {ok: true, errors: [], type: boolean, nodes: 5", "out: {ok: true, errors: [x], type: boolean, nodes: 5", "ensures"),
    ("П7 тип входа", "rptg.yaml", "in: {type: Money, env: *env_money}", "in: {type: 5, env: *env_money}", "не проходит"),
    ("П7 вход не по параметрам", "rptg.yaml", "- in: {results: [{id: p3-money", "- in: {results: [], _x: [{id: p3-money", "не совпадает с параметрами"),
    ("П7 ложное requires", "rptg.yaml", "- in: {results: [{id: p3-money, check: P3, expected: pass, actual: pass, ok: true}, {id: p3-wrong-expect, check: P3, expected: pass, actual: fail, ok: false}]}", "- in: {results: []}", "requires «len(results) >= 1» ложно"),
    ("I5 нет аргумента", "rptg.yaml", '{id: n1, call: "check:evaluate", args: {state: state, event: event, cfg: cfg}}', '{id: n1, call: "check:evaluate", args: {state: state, event: event}}', "I5"),
    ("I9 цикл", "rptg.yaml", "      uses: []\n      effects: []\n      allowed_imports: [json, hashlib, re, decimal, jsonschema, jsonsubschema, z3]", "      uses: [rptg.plan]\n      effects: []\n      allowed_imports: [json, hashlib, re, decimal, jsonschema, jsonsubschema, z3]", "I9"),
    ("имя вне параметров", "rptg.yaml", 'ensures: ["result.kind == query.kind"]\n      effects: []\n      examples:\n        - in: {state: *s_new, query: {kind: status}, cfg: *cfg}\n          out: {kind: status, data', 'ensures: ["result.kind == qery.kind"]\n      effects: []\n      examples:\n        - in: {state: *s_new, query: {kind: status}, cfg: *cfg}\n          out: {kind: status, data', "имена вне параметров"),
    ("П3 тип ребра", "rptg.yaml", '{id: n2, call: "check:summarize", args: {results: n1}}', '{id: n2, call: "check:summarize", args: {results: cfg}}', "П3"),
    ("I11 прогресс", "rptg.yaml", "      est_lines: 400\n", "      est_lines: 7000\n", "I11"),
    ("неизвестный тип", "rptg.yaml", "params: [{name: state, type: State}, {name: query, type: ViewQuery}", "params: [{name: state, type: Stat}, {name: query, type: ViewQuery}", "не найден"),
    ("«*» в точном примере", "rptg.yaml", '"run_tests.py": "*"}}\n          source: user\n          match: subset\n        - in: {state: *s_build, target: {kind: node_package', '"run_tests.py": "*"}}\n          source: user\n        - in: {state: *s_build, target: {kind: node_package', "«*»"),
    ("I3 детей больше предела", "project.yaml", "max_children: 7", "max_children: 6", "I3"),
    # правило Json (map.md §12): любой тип подходит месту Json, но не наоборот
    ("П3 Json в типизированное место", "rptg.check.yaml",
     '{id: n13, call: "cases:pick", args: {case: case, evidences: n12}}',
     '{id: n13, call: "cases:pick", args: {case: case, evidences: n0.state}}', "П3"),
    ("П1 параметр по имени result", "rptg.lang.cl.logic.yaml",
     "params: [{name: answer, type: SolveResult}, {name: smt, type: SmtText}]",
     "params: [{name: result, type: SolveResult}, {name: smt, type: SmtText}]", "имя параметра result занято"),
]


def run_on(design_dir):
    sc.DESIGN = design_dir
    with contextlib.redirect_stdout(io.StringIO()):
        code = sc.check()
    return code, (design_dir / "SELFCHECK.md").read_text(encoding="utf-8")


def copy_design():
    d = Path(tempfile.mkdtemp()) / "design"
    shutil.copytree(ROOT / "design", d)
    return d


def good_case():
    d = Path(tempfile.mkdtemp()) / "design"
    d.mkdir()
    src = ROOT / "tools" / "cases" / "good"
    types = (ROOT / "design" / "types.yaml").read_text(encoding="utf-8")
    (d / "types.yaml").write_text(types + "\n" + (src / "extra_types.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    for f in ("rptg.yaml", "project.yaml"):
        shutil.copy(src / f, d / f)
    return d


def violations(report):
    return [line for line in report.splitlines() if line.startswith("* **")]


def main():
    rows = []
    code, rep = run_on(good_case())
    rows.append(("верный", "независимая маленькая карта проходит без нарушений", code == 0, code, violations(rep)))
    code, rep = run_on(copy_design())
    rows.append(("верный", "карта rptg как есть", code == 0, code, violations(rep)))
    code, rep = run_on(good_case())
    rows.append(("неприменимый", "поэлементное обязательство отображения уходит к Z3, не в нарушения",
                 "поэлементно" in rep and not violations(rep), code, violations(rep)))
    for name, fname, old, new, expect in BAD:
        d = copy_design()
        f = d / fname
        text = f.read_text(encoding="utf-8")
        if old not in text:
            rows.append(("неверный", name, False, "образец не найден", []))
            continue
        f.write_text(text.replace(old, new, 1), encoding="utf-8")
        code, rep = run_on(d)
        rows.append(("неверный", name, code == 1 and expect in rep, code, []))
    d = copy_design()
    text = (d / "rptg.yaml").read_text(encoding="utf-8")
    m = re.search(r'evs_fixed: &evs_fixed\n    - \{check: P1, subject: "design:app.billing", subject_hash: "([0-9a-f]{64})"', text)
    (d / "rptg.yaml").write_text(text.replace(m.group(1), "0" * 64, 1), encoding="utf-8")
    code, rep = run_on(d)
    rows.append(("неверный", "правило хэша разложения", code == 1 and "хэш разложения" in rep, code, []))
    d = copy_design()
    t = (d / "types.yaml").read_text(encoding="utf-8")
    t = t.replace('schema: {type: string, pattern: "^[0-9a-f]{64}$"}', 'schema: {type: string, pattern: "["}', 1)
    (d / "types.yaml").write_text(t, encoding="utf-8")
    code, rep = run_on(d)
    rows.append(("сбой проверки", "неверное регулярное выражение в типе — ERROR, а не нарушение", code == 2 and "ERROR" in rep, code, []))

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failed = 0
    for kind, name, ok, code, viol in rows:
        print(f"{'ок      ' if ok else 'ПРОВАЛ  '} [{kind}] {name}" + ("" if ok else f" — код {code}"))
        if not ok:
            failed += 1
            for v in viol[:5]:
                print("          ", v)
    print(f"\nслучаев {len(rows)}, провалено {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
