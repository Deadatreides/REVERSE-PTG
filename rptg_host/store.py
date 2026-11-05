"""Хранилище проекта (ARCHITECTURE §3): `<проект>/project.yaml` — настройки (Config), `<проект>/.rptg/` —
состояние, журнал, вызовы моделей; `~/.rptg/` (или RPTG_HOME) — таблица компетенций и доверенные проверки.

Состояние пишется атомарно (временный файл и замена). Журнал и вызовы только дописываются; время ставит
оболочка — ядро часов не видит. Ключей здесь нет: запрос к модели сохраняется таким, как ушёл, а ключи
добавляет llm из переменных окружения; тексты вызовов проходят вычистку секретов (ARCHITECTURE §9).
Писатель состояния один: круг и ответы пользователя держат замок `.rptg/lock`. Ручное назначение (`assign`)
правит project.yaml только после того, как новый файл читается как Config.
"""
import contextlib
import copy
import datetime
import json
import os
import re
import time
from decimal import Decimal
from pathlib import Path

import yaml

from rptg import _types as T
from rptg._values import load

EMPTY_TABLE = {"cells": [], "g0": False}
# маски LOGIC §6.6: точный путь, путь.* , путь.** , level:a..b
MASK = re.compile(r"level:\d+(\.\.\d+)?|[^\W\d]\w*(\.[^\W\d]\w*)*(\.\*\*?)?")

# Вычистка секретов — из PTG-MEM (ptg_mem/filters.py), тот же список: модель или пользователь могли
# вписать ключ в замысел, пример или ответ, а вызовы лежат на диске как есть.
SECRET_RE = re.compile(
    r"\b("
    r"uak_[A-Za-z0-9_\-]{16,}"            # Composio user API key
    r"|ak_[A-Za-z0-9_\-]{20,}"            # Composio project key
    r"|ck_[A-Za-z0-9_\-]{16,}"            # Composio consumer key
    r"|sk-[A-Za-z0-9_\-]{20,}"            # OpenAI, Anthropic (sk-ant-...) and compatibles
    r"|gh[pousr]_[A-Za-z0-9]{20,}"        # GitHub tokens
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|glpat-[A-Za-z0-9_\-]{20,}"         # GitLab
    r"|xox[baprs]-[A-Za-z0-9\-]{10,}"     # Slack
    r"|AIza[A-Za-z0-9_\-]{30,}"           # Google
    r"|hf_[A-Za-z0-9]{20,}"               # Hugging Face
    r"|AKIA[0-9A-Z]{16}"                  # AWS access key id
    r"|eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"   # JWT
    r")\b"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)


class Busy(RuntimeError):
    """проект держит другой писатель — круг или ответ в другом процессе"""


def home():
    return Path(os.environ.get("RPTG_HOME") or Path.home() / ".rptg")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def patient(action):
    """На Windows замена файла и его чтение сталкиваются: окно читает state.json, пока круг его заменяет, и одна из
    сторон на миг получает PermissionError (08.10.2026: так падали окно и круг). Это не ошибка данных — действие
    повторяется, пока другая сторона не закроет файл, около секунды; дольше — исключение как есть."""
    for _ in range(50):
        try:
            return action()
        except PermissionError:
            time.sleep(0.02)
    return action()


def write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    patient(lambda: os.replace(tmp, path))


def read_text(path):
    return patient(lambda: path.read_text(encoding="utf-8"))


def scrub(text):
    """Похожее на ключ — в «<secret-removed:префикс>», как в PTG-MEM."""
    def secret(m):
        tok = m.group(1)
        return "<secret-removed:%s>" % (tok.split("_")[0] if "_" in tok[:8] else tok[:4])
    return PRIVATE_KEY_RE.sub("<secret-removed:private-key>", SECRET_RE.sub(secret, text))


def append_rows(path, rows):
    """Строки JSON дописываются в конец файла — журнал и итоги только растут."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_rows(path):
    """Строки JSON файла; строку, оборванную при аварии, пропускает — иначе одна строка остановила бы круг."""
    rows = []
    for line in read_text(path).splitlines() if path.exists() else []:
        with contextlib.suppress(ValueError):
            rows.append(json.loads(line))
    return rows


def save_call(directory, task, request, raw):
    """Запрос попытки — как ушёл (ключей в нём нет) — рядом с сырым ответом (talk: CONTEXT_MODEL §7, F45);
    текст проходит вычистку секретов. Номер — следующий за наибольшим: удалённый файл не освобождает номер, и
    чужой вызов не перезаписывается."""
    directory.mkdir(parents=True, exist_ok=True)
    n = max((int(p.stem) for p in directory.glob("*.json") if p.stem.isdigit()), default=0) + 1
    text = json.dumps({"at": now(), "task": task, "request": request, "raw": raw}, ensure_ascii=False)
    write_atomic(directory / f"{n:05d}.json", scrub(text))


def assign(root, mask, role, operator):
    """Ручное назначение (LOGIC §6.6): маска узлов → роль → оператор из лестницы роли. Новый project.yaml
    сначала читается как Config, затем пишется атомарно: опечатка не должна остановить ядро."""
    path = Path(root) / "project.yaml"
    cfg = yaml.safe_load(read_text(path))
    mask = mask.strip()
    if not MASK.fullmatch(mask) or role not in ("designer", "implementer") or operator not in cfg["operators"] \
            or operator not in cfg["roles"][role]:
        raise ValueError("маска (путь, путь.*, путь.**, level:a..b), роль (designer, implementer) и оператор из лестницы роли")
    cfg.setdefault("overrides", {}).setdefault(mask, {})[role] = operator
    load(T.Config, normalize(copy.deepcopy(cfg)))
    write_atomic(path, yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))


def normalize(cfg):
    """Цены в ядре — десятичные записи, а YAML читает `input: 4` и `input: 0.2` как числа: число цены
    переводится в запись (без экспоненты), остальное — как есть."""
    for op in (cfg.get("operators") or {}).values():
        prices = (op or {}).get("prices") or {}
        for k, v in prices.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                prices[k] = format(Decimal(str(v)), "f")
    return cfg


class Project:
    def __init__(self, root):
        self.root = Path(root)
        self.dir = self.root / ".rptg"

    def exists(self):
        return (self.dir / "state.json").exists()

    def config(self):
        """project.yaml; список доверенных проверок — из selftest в ~/.rptg, если проект не задал свой."""
        cfg = normalize(yaml.safe_load(read_text(self.root / "project.yaml")))
        trusted = home() / "trusted.json"
        if "trusted" not in cfg and trusted.exists():
            cfg["trusted"] = json.loads(read_text(trusted))
        return cfg

    def table(self):
        path = home() / "competence.json"
        return json.loads(read_text(path)) if path.exists() else dict(EMPTY_TABLE)

    def load_state(self):
        return json.loads(read_text(self.dir / "state.json"))

    def save_state(self, state):
        write_atomic(self.dir / "state.json", json.dumps(state, ensure_ascii=False, indent=1))

    @contextlib.contextmanager
    def lock(self):
        """Один писатель (D14): круг и ответы держат замок — блокировку байта файла `.rptg/lock`. Второй
        писатель получает Busy, а не перезапись чужого перехода; умерший процесс замок не оставляет — его
        снимает ОС."""
        self.dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.dir / "lock", os.O_RDWR | os.O_CREAT)
        try:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise Busy(f"проект занят: круг или ответ идёт в другом процессе или окне ({self.root})") from None
            try:
                yield
            finally:
                if os.name == "nt":
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(fd)

    def append(self, name, rows):
        append_rows(self.dir / name, rows)

    def record(self, event, transition):
        """Событие и записи журнала перехода — с временем оболочки."""
        at = now()
        self.append("journal.jsonl", [{"at": at, "event": event["kind"]}] +
                    [{"at": at, **entry} for entry in transition["journal"]])

    def journal(self):
        return read_rows(self.dir / "journal.jsonl")

    def save_call(self, task, request, raw):
        save_call(self.dir / "calls", task, request, raw)
