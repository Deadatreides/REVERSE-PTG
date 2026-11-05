"""Проект kit: папка программы и её состояние в `.rptg-kit/`.

Программа лежит в папке как есть: пакет, pyproject.toml, tach.toml, tests/. Состояние — `.rptg-kit/state.json`
(атомарная замена), журнал — `.rptg-kit/journal.jsonl` (только дописывается). Писатель один: каждая сдача и
каждый шаг обхода держат замок — поток сервера и байт файла `.rptg-kit/lock` (параллельные субагенты ждут
очереди, а не перезаписывают друг друга). Проверки идут в копии папки, в настоящую попадает только принятое;
заменённые файлы уходят в `.rptg-kit/trash/`, а не удаляются.
"""
import contextlib
import datetime
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

KIT_DIR = ".rptg-kit"
CACHES = (KIT_DIR, "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".hypothesis", ".tach", ".crosshair", "*.pyc",
          ".venv", "venv", ".git")  # окружение проекта не копируется: копия проверяется им на месте (checks.python_for)
_THREAD = threading.RLock()


class Busy(RuntimeError):
    """проект держит другой писатель дольше срока ожидания"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def patient(action):
    """Замена файла и его чтение на Windows сталкиваются (PermissionError на миг) — повтор около секунды."""
    for _ in range(50):
        try:
            return action()
        except PermissionError:
            time.sleep(0.02)
    return action()


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    patient(lambda: os.replace(tmp, path))


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.dir = self.root / KIT_DIR

    def exists(self):
        return (self.dir / "state.json").exists()

    def load(self):
        return json.loads(patient(lambda: (self.dir / "state.json").read_text(encoding="utf-8")))

    def save(self, state):
        write_atomic(self.dir / "state.json", json.dumps(state, ensure_ascii=False, indent=1))

    def log(self, event, **data):
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "journal.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "event": event, **data}, ensure_ascii=False) + "\n")

    @contextlib.contextmanager
    def lock(self, wait=900):
        """Поток сервера и процесс: замок байта `.rptg-kit/lock`, ожидание до `wait` секунд."""
        with _THREAD:
            self.dir.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.dir / "lock", os.O_RDWR | os.O_CREAT)
            try:
                deadline = time.time() + wait
                while True:
                    try:
                        if os.name == "nt":
                            import msvcrt
                            os.lseek(fd, 0, os.SEEK_SET)
                            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.time() > deadline:
                            raise Busy(f"проект занят другим писателем дольше {wait} с: {self.root}") from None
                        time.sleep(0.2)
                try:
                    yield
                finally:
                    if os.name == "nt":
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            finally:
                os.close(fd)

    # --- файлы программы -------------------------------------------------------------------------------------
    def path_of(self, module):
        """Модуль узла → путь от корня: пакет (…/__init__.py), если он есть, иначе модуль (….py)."""
        base = Path(*module.split("."))
        return base / "__init__.py" if (self.root / base / "__init__.py").exists() else base.with_suffix(".py")

    def read(self, module):
        return (self.root / self.path_of(module)).read_text(encoding="utf-8")

    def stage(self):
        """Копия программы во временной папке — проверки идут там."""
        from .checks import MARK, python_for  # checks импортирует project — здесь, а не вверху
        tmp = Path(tempfile.mkdtemp(prefix="rptg-kit-"))
        shutil.copytree(self.root, tmp / "p", ignore=shutil.ignore_patterns(*CACHES))
        (tmp / "p" / MARK).write_text(python_for(self.root), encoding="utf-8")
        # Примеры и тесты — в чистой папке с копией tests/fixtures, как у итогового `pytest` в проекте: иначе пример,
        # читающий исходник программы, проходил проверки kit и падал в проекте (17.10, graphlm.gxs.pagefile).
        from .rules import CONFTEST
        (tmp / "p" / "conftest.py").write_text(CONFTEST, encoding="utf-8")
        return tmp / "p"

    def discard(self, staged):
        """Копия программы после проверок — удаляется вместе с её временной папкой (11.10.2026 их скопилось 321,
        3,7 ГБ, и диск C кончился). Принятое к этому времени уже в программе (apply)."""
        shutil.rmtree(Path(staged).parent, ignore_errors=True)

    def apply(self, staged, paths):
        """Принятые файлы из копии — в программу; прежние версии — в корзину `.rptg-kit/trash/<время>/`."""
        stamp = now().replace(":", "").replace("-", "")
        for rel in paths:
            target = self.root / rel
            if target.exists():
                keep = self.dir / "trash" / stamp / rel
                keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, keep)
            write_atomic(target, (staged / rel).read_text(encoding="utf-8"))

    def retire(self, rels):
        """Файлы снятого поддерева — в корзину (не удаляются)."""
        stamp = now().replace(":", "").replace("-", "")
        for rel in rels:
            target = self.root / rel
            if target.exists():
                keep = self.dir / "trash" / stamp / rel
                keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), keep)


def module_of(rel):
    """Путь от корня → модуль: app/billing/__init__.py → app.billing, app/money.py → app.money."""
    parts = Path(rel).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def parent_of(module):
    return module.rpartition(".")[0] or None
