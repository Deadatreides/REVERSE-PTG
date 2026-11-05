"""Проверки kit — готовыми инструментами, в копии программы.

Карточки (до кода): mypy по заглушкам — типы связей; tach — граф импортов (запрещённое ребро, цикл); ruff и
deal lint — запреты и побочные эффекты; сверка примеров с условиями — doctest, где заглушка отвечает ожиданием
своего примера, а условия проверяет сам deal во время вызова. Код: то же плюс radon (сложность не выше 1,5·D + 5 —
закон, измеренный на 105 функциях rptg, BASIS А11), doctest с настоящим телом, deal.cases (Hypothesis выводит
сотни входов из условий pre и проверяет ensure) и CrossHair (решатель ищет вход-нарушитель). Своё здесь — только
соглашения карточек и правило видимости зависимостей по дереву.

Код моделей исполняется в отдельных процессах с тайм-аутом и чистым окружением: ключей API и настроек
оболочки он не видит. Отчёт инструмента возвращается модели как есть, только пути — от корня программы.
"""
import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from radon.complexity import cc_visit

from . import cards, rules
from .project import module_of, parent_of

ALLOWED_ENV = {"PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE",
               "LOCALAPPDATA", "APPDATA", "LANG", "LC_ALL"}
LIMIT = 4000
REPLAY = '''"""Сверка примеров с условиями до кода (rptg kit): заглушка отвечает ожиданием своего примера, а условия
проверяет сам deal — до вызова pre, после — ensure и post."""
import ast
import builtins
import doctest
import inspect
import sys


def answer(module_name, name, call):
    module = sys.modules[module_name]
    fn = getattr(module, name)
    ns = vars(module)
    for ex in doctest.DocTestParser().get_examples(fn.__doc__ or ""):
        node = ast.parse(ex.source.strip(), mode="eval").body
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name):
            continue
        args = [eval(ast.unparse(a), ns) for a in node.args]
        kwargs = {k.arg: eval(ast.unparse(k.value), ns) for k in node.keywords}
        bound = inspect.signature(fn).bind(*args, **kwargs)
        bound.apply_defaults()
        if dict(bound.arguments) != call:
            continue
        if ex.exc_msg is not None:
            last = ex.want.strip().splitlines()[-1]
            kind = last.split(":")[0].strip()
            # exc_msg у doctest — «Тип: сообщение», как печатает traceback; исключению нужно только сообщение
            head, sep, message = ex.exc_msg.strip().partition(":")
            message = message.strip() if sep else ""
            try:  # KeyError печатает repr сообщения: 'текст' — исключению нужен сам текст
                literal = ast.literal_eval(message)
                message = literal if isinstance(literal, str) else message
            except (ValueError, SyntaxError):
                pass
            raise eval(kind, {**vars(builtins), **ns})(message)
        if not ex.want.strip():
            return None  # пустой вывод примера — функция вернула None
        return eval(ex.want, ns)
    raise NotImplementedError(f"у {name} нет примера с такими аргументами: {call!r}")
'''


@dataclass
class Finding:
    tool: str
    text: str

    def __str__(self):
        return f"[{self.tool}] {self.text}"


def env_for(root):
    env = {k: v for k, v in os.environ.items() if k.upper() in ALLOWED_ENV}
    return {**env, "PYTHONPATH": str(root), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1"}


# --- окружение проверок ----------------------------------------------------------------------------------------
TOOLS = ("mypy", "tach", "ruff", "deal", "crosshair", "pytest", "hypothesis")
MARK = ".rptg-python"  # в копии программы: каким интерпретатором её проверять
DISTS = {"yaml": "PyYAML", "PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn", "bs4": "beautifulsoup4",
         "crosshair": "crosshair-tool", "dateutil": "python-dateutil"}
PROBE = "import importlib.util, sys; print(' '.join(m for m in sys.argv[1:] if importlib.util.find_spec(m) is None))"


def python_for(root):
    """Интерпретатор проверок программы: её собственное окружение <папка>/.venv, если оно есть, иначе — окружение
    сервера kit. 11.10.2026 сервер плагина шёл из копии в кэше Claude Code, где не было detect-secrets, и
    проектировщик потерял на этом две сдачи из трёх."""
    venv = Path(root) / ".venv"
    for exe in (venv / "Scripts" / "python.exe", venv / "bin" / "python"):
        if exe.exists():
            return str(exe)
    return sys.executable


def interpreter(root):
    mark = Path(root) / MARK
    return mark.read_text(encoding="utf-8").strip() if mark.exists() else sys.executable


def third_party(files, package):
    """Пакеты не из стандартной библиотеки, которые импортируют модули программы {путь: текст}."""
    names = set()
    for text in files.values():
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                names.add(n.module.split(".")[0])
    return sorted(names - set(sys.stdlib_module_names) - {package, "_rptg_replay", "__future__"})


def dist_of(name):
    return DISTS.get(name, name.replace("_", "-"))


def environment(root, package):
    """Всё ли есть в окружении проверок: пакеты, которые импортирует программа, и сами проверки. Нехватка — не
    ошибка сдачи: отчёт говорит, что поставить и куда, а сдача не засчитывается (flow.submit)."""
    files = {str(p): p.read_text(encoding="utf-8") for p in (Path(root) / package).rglob("*.py")}
    wanted = sorted(set(third_party(files, package)) | set(TOOLS))
    python = interpreter(root)
    try:
        p = subprocess.run([python, "-c", PROBE, *wanted], cwd=root, env=env_for(root), stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=60)
        missing = p.stdout.split() if p.returncode == 0 else [f"(интерпретатор не запустился: {p.stderr.strip()[:300]})"]
    except (OSError, subprocess.TimeoutExpired) as e:
        missing = [f"(интерпретатор не запустился: {e})"]
    if not missing:
        return []
    install = " ".join(dist_of(m) for m in missing if not m.startswith("("))
    return [Finding("env", f"в окружении проверок нет: {', '.join(missing)} — интерпретатор {python}. Сдача не засчитана: это не "
                           f"ошибка сдачи. Если это опечатка в импорте — исправьте импорт и сдайте снова; если пакет нужен — "
                           f"ответьте «сдался: окружение», главный чат поставит: \"{python}\" -m pip install {install}")]


def run(args, root, timeout, prefix=("-m",)):
    """`python -m <инструмент>` в копии программы; итог — код выхода и вывод с путями от корня. Ввод — пустой: у
    сервера MCP ввод — это канал протокола, и унаследовав его, инструменты под Claude Code висели до тайм-аута
    (живая проверка плагина 10.10.2026; тесты звали проверки не через канал и этого не видели). Интерпретатор —
    тот, что записан в копии (python_for)."""
    try:
        p = subprocess.run([interpreter(root), *prefix, *args], cwd=root, env=env_for(root), stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
        code, out = p.returncode, (p.stdout + "\n" + p.stderr).strip()
    except subprocess.TimeoutExpired:
        code, out = -1, f"тайм-аут {timeout} с"
    for prefix in (str(root) + os.sep, str(root)):
        out = out.replace(prefix, "")
    return code, out


def trim(text, keep=None):
    lines = [line for line in text.splitlines() if line.strip()]
    if keep:
        picked = [line for line in lines if any(k in line for k in keep)]
        lines = picked or lines
    out = "\n".join(lines)
    return out if len(out) <= LIMIT else out[:LIMIT] + "\n… (обрезано)"


def tool(name, args, root, timeout, keep=None, prefix=("-m",)):
    code, out = run(args, root, timeout, prefix)
    return [] if code == 0 else [Finding(name, trim(out, keep))]


def mypy(root, package):
    return tool("mypy", ["mypy", package, "--no-error-summary", "--show-error-codes"], root, 300, keep=("error:",))


def tach(root):
    return tool("tach", ["tach", "check"], root, 120, keep=("[FAIL]", "Cannot", "circular", "Circular"))


def ruff(root, rels):
    return tool("ruff", ["ruff", "check", "--output-format", "concise", "--no-cache", *rels], root, 120, keep=(": ",))


STUB_LINE = "raise NotImplementedError"


def deal_lint(root, rels):
    """deal lint. DEL021 («исключение не объявлено в @deal.raises») на строке заглушки — не ошибка карточки: тело ещё
    не написано (11.10.2026 так отвергалась любая карточка с @deal.raises). Тело-заглушку kit и так не примет."""
    code, out = run(["deal", "lint", "--json", "--nocolor", *rels], root, 120)
    if code == 0:
        return []
    rows = []
    for line in out.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            rows.append(line)
            continue
        content = str(e.get("content", "")).strip()
        if str(e.get("code")) == "DEL021" and content.startswith(STUB_LINE):
            continue
        rows.append(f"{e.get('path')}:{e.get('row')}: {e.get('code')} {e.get('message')} — {content}")
    return [Finding("deal lint", trim("\n".join(rows)))] if rows else []


def pytest(root, ids, name="pytest"):
    if not ids:
        return []
    return tool(name, ["pytest", "-q", "--tb=short", "-p", "no:cacheprovider", "--no-header", *ids], root, 600,
                keep=None)


# CrossHair с проверяемыми модулями, импортированными до его защиты от побочных эффектов (auditwall): эффекты
# импорта проходят — numpy под Windows добавляет каталог DLL, platform спрашивает имя машины (11.10.2026 так
# CrossHair не загрузил ни одного модуля memshell), — а проверяемый код остаётся под защитой.
CROSSHAIR = """import importlib, sys
for m in sys.argv[1].split(","):
    importlib.import_module(m)
from crosshair.main import main
main(["check", *sys.argv[2:]])
"""


def crosshair(root, qualified, seconds):
    if not qualified:
        return []
    modules = ",".join(sorted({q.rsplit(".", 1)[0] for q in qualified}))
    return tool("crosshair", [CROSSHAIR, modules, "--analysis_kind=deal", f"--per_condition_timeout={seconds}", *qualified], root, 900,
                keep=("error:",), prefix=("-c",))


def complexity(source, functions):
    """radon: сложность каждой функции не выше 1,5·D + 5 (BASIS А11: D_код = 1,49·D − 1,27 на 105 функциях, +2σ)."""
    out = []
    d_of = {c.name: c.d for c in cards.cards(source)}
    for block in cc_visit(source):
        if block.name in functions and d_of.get(block.name):
            limit = 1.5 * d_of[block.name] + 5
            if block.complexity > limit:
                out.append(Finding("radon", f"{block.name}: сложность {block.complexity} больше предела карточки "
                                            f"{limit:g} (1,5·D + 5 при D = {d_of[block.name]}) — упростите или верните карточку на разделение"))
    return out


# --- соглашения карточек и граф ------------------------------------------------------------------------------
def conventions(rel, text, *, own, frozen, kind_expected=None):
    """Карточки модуля по правилам kit. own — модуль самого узла (его тела — связка), иначе дочерний (заглушки)."""
    out, where = [], rel
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [Finding("syntax", f"{where}:{e.lineno}: {e.msg}")]
    module = module_of(rel)
    is_types = module.endswith(".types") and module.count(".") == 1
    if is_types:
        if cards.functions(tree):
            out.append(Finding("card", f"{where}: в типах только классы данных, функции — в узлах"))
        return out
    kind = cards.node_kind(text)
    if kind not in cards.KINDS:
        out.append(Finding("card", f"{where}: в описании модуля нет строки «node: leaf» или «node: composite»"))
    elif kind == "composite" and not rel.endswith("__init__.py"):
        out.append(Finding("card", f"{where}: составной узел — пакет (<имя>/__init__.py)"))
    elif kind == "leaf" and rel.endswith("__init__.py"):
        out.append(Finding("card", f"{where}: лист — модуль (<имя>.py), не пакет"))
    if kind_expected and kind and kind != kind_expected:
        out.append(Finding("card", f"{where}: вид узла {kind}, а карточка родителя назначила {kind_expected}"))
    found = cards.cards(text)
    if not found:
        out.append(Finding("card", f"{where}: в узле нет ни одной функции-карточки"))
    for c in found:
        at = f"{where}:{c.lineno} {c.name}"
        if c.d is None or c.d < 1:
            out.append(Finding("card", f"{at}: в описании нет строки «D: <число решений>»"))
        if len(c.examples) < 1:
            out.append(Finding("card", f"{at}: нет примеров doctest (>>> вызов, ниже — точный repr результата)"))
        for ex in c.examples:
            try:
                call = ast.parse(ex.source.strip(), mode="eval").body
                single = isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == c.name
            except SyntaxError:
                single = False
            if not single:
                out.append(Finding("card", f"{at}: пример «{ex.source.strip()}» — не один вызов {c.name}(…) с готовыми значениями"))
        if "has" not in c.kinds:
            out.append(Finding("card", f"{at}: нет @deal.has(…) — побочные эффекты объявляются явно (() — чистая функция)"))
        if kind == "leaf" and not c.guarantees:
            out.append(Finding("card", f"{at}: у функции листа нет гарантии @deal.ensure или @deal.post"))
        if own:
            if frozen and frozen.get(c.name) and frozen[c.name] != c.digest:
                out.append(Finding("card", f"{at}: карточку узла менять нельзя (декораторы, подпись, описание) — только тело"))
            if kind == "composite" and c.stub:
                out.append(Finding("card", f"{at}: тело составного узла — связка из вызовов детей, а не заглушка"))
        elif not c.stub:
            out.append(Finding("card", f"{at}: у дочерней карточки тело — `raise NotImplementedError`: код пишет исполнитель"))
    if own and frozen:
        missing = sorted(set(frozen) - {c.name for c in found})
        if missing:
            out.append(Finding("card", f"{where}: пропали функции карточки узла: {', '.join(missing)}"))
    return out


def visibility(deps, package, checked):
    """Правило видимости: модуль может импортировать типы, своих детей, братьев и то, что может его родитель
    (кроме себя и предков). Импорты объявляет карточка — исполнитель их не добавит (это держит tach)."""
    out = []
    types = f"{package}.types"
    for m in sorted(checked):
        parent = parent_of(m)
        children = {x for x in deps if parent_of(x) == m}
        siblings = {x for x in deps if parent_of(x) == parent and x != m} if parent else set()
        inherited = set(deps.get(parent, ())) if parent else set()
        ancestors = {".".join(m.split(".")[:i]) for i in range(1, m.count(".") + 1)}
        allowed = ({types} | children | siblings | inherited) - {m} - ancestors
        for dep in deps.get(m, ()):
            if dep.startswith("."):
                out.append(Finding("graph", f"{m}: относительный импорт {dep} — только абсолютные ({package}.…)"))
            elif dep not in allowed:
                out.append(Finding("graph", f"{m} не может зависеть от {dep}: видны только типы, дети, братья и то, что может "
                                            f"родитель {parent or '—'}"))
    return out


def orphans(deps, node, children):
    """Каждый новый ребёнок узла нужен: его импортирует сам узел или брат."""
    users = {x for m, ds in deps.items() for x in ds}
    return [Finding("graph", f"{c}: дочерний узел никто не использует — уберите его или вызовите из {node}") for c in sorted(children)
            if c not in users]


# --- сверка примеров с условиями -------------------------------------------------------------------------------
def replay(root, package, rels):
    """Примеры карточек против их же условий, до кода: тело каждой функции заменяется ответом из её примера,
    doctest вызывает функцию через deal — тот проверяет pre на входе и ensure/post на ожидании примера."""
    ids = []
    for rel in rels:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        bodies = {}
        for fn in cards.functions(tree):
            call = "{" + ", ".join(f'"{p}": {p}' for p in cards.params(fn)) + "}"
            bodies[fn.name] = f'import _rptg_replay\nreturn _rptg_replay.answer(__name__, "{fn.name}", {call})'
            if ast.get_docstring(fn) and ">>>" in ast.get_docstring(fn):
                ids.append(f"{rel}::{module_of(rel)}.{fn.name}")
        if bodies:
            path.write_text(cards.replace_bodies(text, bodies), encoding="utf-8")
    (root / "_rptg_replay.py").write_text(REPLAY, encoding="utf-8")
    found = pytest(root, ids, name="примеры против условий")
    if found:
        return found
    funcs = [f"{module_of(rel)}:{n}" for rel in rels
             for n in pure((root / rel).read_text(encoding="utf-8"), [c.name for c in cards.cards((root / rel).read_text(encoding="utf-8"))])]
    if not funcs:
        return []
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_rptg_conditions.py").write_text(conditions_test(funcs), encoding="utf-8")
    return pytest(root, [f"tests/test_rptg_conditions.py::{conditions_id(f)}" for f in funcs], name="условия на случайных входах")


CONDITIONS_RUNNER = '''
SETTINGS = hypothesis.settings(database=None, max_examples=60, deadline=None, verbosity=hypothesis.Verbosity.quiet,
                               suppress_health_check=list(hypothesis.HealthCheck))


def conditions(func):
    """Условия карточки на случайных входах (тело — ответ примера, до кода). Условие обязано быть выражением без
    исключений: deal проверяет все pre подряд, даже после ложного, — `x[0]` при пустом x или `log(v)` при v <= 0 падает
    уже при сборке (17.10, graphlm: replay, derive). Исключение не из условия (нет ответа примера) — не дефект."""
    path = inspect.getsourcefile(inspect.unwrap(func))

    def run():
        try:
            cases = deal.cases(func, count=60, settings=SETTINGS)
            for case in cases:
                try:
                    case()
                except (deal.ContractError, NotImplementedError):
                    pass
                except Exception as e:
                    tb = e.__traceback__
                    while tb is not None:
                        code = tb.tb_frame.f_code
                        if code.co_name == "<lambda>" and code.co_filename == path:
                            pytest.fail(f"условие (строка {tb.tb_lineno}) бросает {type(e).__name__}: {e} на входе {case.kwargs!r}"
                                        " — защитите его внутри того же выражения (len(x) >= 1 and x[0] …)")
                        tb = tb.tb_next
        except (hypothesis.errors.Unsatisfiable, hypothesis.errors.FailedHealthCheck):
            pass
    return run
'''


def conditions_test(functions):
    lines = ['"""Условия карточек на случайных входах (раскладка, до кода). Пишет rptg kit."""', "import inspect",
             "import sys", "", "import deal", "import hypothesis", "import pytest", ""]
    lines += [f"import {m}" for m in sorted({f.split(':')[0] for f in functions})] + [CONDITIONS_RUNNER]
    for f in sorted(functions):
        module, name = f.split(":")
        lines.append(f"{conditions_id(f)} = conditions(sys.modules[{module!r}].{name})")
    return "\n".join(lines) + "\n"


def conditions_id(function):
    module, name = function.split(":")
    return f"test_{module.replace('.', '_')}__{name}"


# --- ступени ---------------------------------------------------------------------------------------------------
def design(stage, package, node, own_rel, child_rels, frozen, first_root=False):
    """Разложение узла: своя связка + карточки детей. stage — копия программы с присланными файлами."""
    files = {str(p.relative_to(stage)).replace(os.sep, "/"): p.read_text(encoding="utf-8")
             for p in (stage / package).rglob("*.py")}
    out = environment(stage, package)
    if out:
        return out
    for rel in [own_rel, *child_rels]:
        if rel.endswith("types.py") and module_of(rel) == f"{package}.types":
            out += conventions(rel, files[rel], own=False, frozen=None)
        else:
            out += conventions(rel, files[rel], own=rel == own_rel, frozen=frozen if rel == own_rel and not first_root else None)
    if out:
        return out  # форма не та — дальше не гоним: отчёт короче и по делу
    deps = rules.graph(files, package)
    checked = {module_of(r) for r in [own_rel, *child_rels]} - {f"{package}.types"}
    out += visibility(deps, package, checked)
    out += orphans(deps, node, {module_of(r) for r in child_rels} - {f"{package}.types"})
    (stage / "tach.toml").write_text(rules.tach_toml(deps), encoding="utf-8")
    rels = [own_rel, *child_rels]
    out += mypy(stage, package) + tach(stage) + ruff(stage, rels) + deal_lint(stage, rels)
    out += complexity(files[own_rel], {c.name for c in cards.cards(files[own_rel])})
    if out:
        return out
    return replay_in_copy(stage, package, [r for r in rels if not r.endswith("types.py")])


def replay_in_copy(stage, package, rels):
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="rptg-replay-")) / "p"
    shutil.copytree(stage, tmp)
    try:
        return replay(tmp, package, rels)
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def implement(stage, package, rel, names, seconds):
    """Код листа: тела функций вклеены в карточку в копии программы."""
    text = (stage / rel).read_text(encoding="utf-8")
    module = module_of(rel)
    out = environment(stage, package)
    if out:
        return out
    out = complexity(text, set(names))
    out += mypy(stage, package) + tach(stage) + ruff(stage, [rel]) + deal_lint(stage, [rel])
    if out:
        return out
    return behaviour(stage, package, rel, module, names, seconds)


def pure(text, names):
    """Функции без побочных эффектов: только им — случайные входы (deal.cases) и решатель (CrossHair). Функция с
    @deal.has("io" | "write" | …) получила бы от Hypothesis случайный путь и писала бы по нему; её проверка — примеры,
    а они идут в копии программы, cwd — копия."""
    effectful = {c.name for c in cards.cards(text) if c.effects}
    return [n for n in names if n not in effectful]


def behaviour(stage, package, rel, module, names, seconds):
    """Поведение: doctest (примеры карточки), deal.cases (свойства из условий, Hypothesis), CrossHair."""
    calm = pure((stage / rel).read_text(encoding="utf-8"), names)
    funcs = [f"{module}:{n}" for n in calm]
    (stage / "tests").mkdir(exist_ok=True)
    (stage / "tests" / "test_rptg_cases.py").write_text(rules.cases_test(package, funcs), encoding="utf-8")
    out = pytest(stage, [f"{rel}::{module}.{n}" for n in names] + [rules.case_id(f) for f in funcs])
    if out:
        return out
    if solver_blind((stage / rel).read_text(encoding="utf-8"), package):
        return []
    return crosshair(stage, [f"{module}.{n}" for n in calm], seconds)


def solver_blind(text, package):
    """Модуль на сторонних библиотеках (numpy, scipy, networkx, lancedb …): CrossHair исполняет символьно только
    чистый Python, а такие библиотеки — машинный код или собирают функции через exec, и решатель падает внутри них
    (networkx: «exec() globals must be a dict»). Их свойства проверяют примеры и deal.cases."""
    return any(m != "deal" for m in third_party({"m.py": text}, package))


def integrate(stage, package, rel, names, seconds):
    """Составной узел, когда все дети написаны: его примеры и свойства — уже с настоящими детьми."""
    return environment(stage, package) or mypy(stage, package) + tach(stage) or behaviour(stage, package, rel, module_of(rel), names, seconds)
