"""Карточки: функция-заглушка в модуле узла.

Карточка — подпись с типами, условия deal (pre, ensure/post, has, raises), описание с числом решений «D: n» и
примерами doctest; тело — `raise NotImplementedError`, пока функцию не написали. Модуль узла объявляет вид строкой
«node: leaf» или «node: composite» в своём описании. Разбор, отпечаток и вклейка тела — модулем ast, примеры —
doctest.DocTestParser: оба из стандартной библиотеки.
"""
import ast
import doctest
import hashlib
import re
import textwrap
from dataclasses import dataclass, field

KINDS = ("leaf", "composite")
NODE_RE = re.compile(r"^\s*node:\s*(\w+)\s*$", re.M)
D_RE = re.compile(r"^\s*D:\s*(\d+)\s*$", re.M)
GUARANTEES = ("ensure", "post")


@dataclass
class Card:
    name: str
    lineno: int
    signature: str
    decorators: list
    doc: str
    examples: list
    d: int | None
    stub: bool
    kinds: list = field(default_factory=list)
    effects: list = field(default_factory=list)  # маркеры @deal.has(...): пусто — чистая функция

    @property
    def digest(self):
        """Отпечаток карточки — декораторы, подпись и описание, без тела: его сверяют, когда тело меняется."""
        text = "\n".join([*self.decorators, self.signature, self.doc])
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @property
    def guarantees(self):
        return sum(kind in GUARANTEES for kind in self.kinds)


def signature(fn):
    return f"def {fn.name}({ast.unparse(fn.args)})" + (f" -> {ast.unparse(fn.returns)}" if fn.returns else "")


def body_of(fn):
    """Тело без описания."""
    return fn.body[1:] if ast.get_docstring(fn) is not None else fn.body


def is_stub(fn):
    body = body_of(fn)
    if len(body) != 1 or not isinstance(body[0], ast.Raise) or body[0].exc is None:
        return False
    exc = body[0].exc.func if isinstance(body[0].exc, ast.Call) else body[0].exc
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def contract_kind(dec):
    """`@deal.pre(...)` → «pre»; чужой декоратор → пусто."""
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "deal":
        return target.attr
    return ""


def functions(tree):
    return [n for n in tree.body if isinstance(n, ast.FunctionDef)]


def effects(fn):
    """Маркеры побочных эффектов из `@deal.has("io", "write", …)`; у чистой функции — пусто."""
    return [a.value for d in fn.decorator_list if isinstance(d, ast.Call) and contract_kind(d) == "has"
            for a in d.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]


def cards(source):
    out = []
    for fn in functions(ast.parse(source)):
        doc = ast.get_docstring(fn) or ""
        m = D_RE.search(doc)
        out.append(Card(name=fn.name, lineno=fn.lineno, signature=signature(fn), decorators=[ast.unparse(d) for d in fn.decorator_list],
                        doc=doc, examples=doctest.DocTestParser().get_examples(doc), d=int(m.group(1)) if m else None,
                        stub=is_stub(fn), kinds=[contract_kind(d) for d in fn.decorator_list], effects=effects(fn)))
    return out


def node_kind(source):
    doc = ast.get_docstring(ast.parse(source)) or ""
    m = NODE_RE.search(doc)
    return m.group(1) if m else None


def imports(source, package):
    """Импорты своего пакета: (модуль, имя) — `from app.billing import lines` даёт ("app.billing", "lines");
    относительные импорты — ("." * уровень + модуль, имя), их правила карточки не допускают."""
    out = []
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Import):
            out += [(a.name, None) for a in n.names if a.name.split(".")[0] == package]
        elif isinstance(n, ast.ImportFrom):
            module = "." * n.level + (n.module or "")
            if n.level or module.split(".")[0] == package:
                out += [(module, a.name) for a in n.names]
    return out


def resolve(pairs, known):
    """Модули-зависимости: `from x import y` — модуль x.y, если он есть среди узлов, иначе x."""
    deps = set()
    for module, name in pairs:
        deps.add(f"{module}.{name}" if name and f"{module}.{name}" in known else module)
    return deps


def _segment(code, stmts):
    """Текст операторов присланного тела с отступом от нуля (комментарии внутри сохраняются)."""
    lines = code.splitlines()
    first, last = stmts[0], stmts[-1]
    chunk = lines[first.lineno - 1:last.end_lineno]
    chunk[0] = " " * first.col_offset + chunk[0][first.col_offset:]
    return textwrap.dedent("\n".join(chunk))


def splice(source, code):
    """Тела присланных функций — в карточки модуля. Декораторы, подписи и описания остаются из карточки: в
    присланном берутся только тела. Прислать можно любые функции модуля, каждую — с той же подписью; кроме
    определений функций, ничего (импорты объявляет карточка). Итог — новый текст модуля и имена вклеенных."""
    code = textwrap.dedent(code).strip("\n")
    try:
        sent = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"код не разбирается: {e}") from None
    extra = [n for n in sent.body if not isinstance(n, ast.FunctionDef)]
    if extra:
        raise ValueError(f"кроме функций модуля, ничего присылать нельзя (строка {extra[0].lineno}: {type(extra[0]).__name__}) — "
                         "импорты и типы объявляет карточка")
    tree = ast.parse(source)
    known = {fn.name: fn for fn in functions(tree)}
    patches = []
    for fn in functions(sent):
        orig = known.get(fn.name)
        if orig is None:
            raise ValueError(f"в карточке нет функции {fn.name}: новые имена не допускаются (вложенные помощники — внутри тела)")
        if signature(fn) != signature(orig):
            raise ValueError(f"подпись {fn.name} не совпадает с карточкой: нужна {signature(orig)}")
        new_body = body_of(fn)
        if not new_body:
            raise ValueError(f"у {fn.name} пустое тело")
        old_body = body_of(orig)
        if old_body[0].lineno == orig.lineno:
            raise ValueError(f"тело {fn.name} в карточке стоит на строке def — так карточку не пишут")
        indent = " " * old_body[0].col_offset
        text = textwrap.indent(_segment(code, new_body), indent)
        patches.append((old_body[0].lineno, old_body[-1].end_lineno, text.splitlines()))
    lines = source.splitlines()
    for start, end, new in sorted(patches, reverse=True):
        lines[start - 1:end] = new
    out = "\n".join(lines) + "\n"
    before = {c.name: c.digest for c in cards(source)}
    after = {c.name: c.digest for c in cards(out)}
    if before != after:  # вклейка не должна менять карточку: иначе это ошибка самой склейки
        raise ValueError("вклейка изменила карточку — тело присланной функции вышло за её пределы")
    return out, [fn.name for fn in functions(sent)]


def replace_bodies(source, bodies):
    """Тела функций — заданным текстом (для сверки примеров с условиями): {имя: текст тела без отступа}."""
    tree = ast.parse(source)
    lines = source.splitlines()
    for fn in sorted((f for f in functions(tree) if f.name in bodies), key=lambda f: f.lineno, reverse=True):
        old = body_of(fn)
        indent = " " * old[0].col_offset
        lines[old[0].lineno - 1:old[-1].end_lineno] = textwrap.indent(bodies[fn.name], indent).splitlines()
    return "\n".join(lines) + "\n"


def keep_bodies(card, built, names):
    """Карточка модуля, где у функций names тела — из собранного модуля built (их карточки не менялись)."""
    bodies = {fn.name: _segment(built, body_of(fn)) for fn in functions(ast.parse(built)) if fn.name in names}
    return replace_bodies(card, bodies)


def as_card(source):
    """Модуль без тел: каждая функция — `raise NotImplementedError` (карточка собранного модуля — к сравнению)."""
    return replace_bodies(source, {fn.name: "raise NotImplementedError" for fn in functions(ast.parse(source))})


def params(fn_source_or_node):
    """Имена параметров функции в порядке подписи (с *args и **kwargs)."""
    fn = fn_source_or_node
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if a.vararg:
        names.append(a.vararg.arg)
    names += [x.arg for x in a.kwonlyargs]
    if a.kwarg:
        names.append(a.kwarg.arg)
    return names
