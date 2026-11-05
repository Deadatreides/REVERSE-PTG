"""Песочница (ARCHITECTURE §6): набор файлов сборки — во временную папку, `python run_tests.py <что>` в
подпроцессе с тайм-аутом, отчёт report.json — ядру как есть.

Окружение чистое, по белому списку: код модели не видит ключей API и настроек Python оболочки. Код 2 без
отчёта — сбой оснастки (ядро ставит unknown), тайм-аут — fail.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WHAT = {"e1_mypy": "mypy", "e2_e3": "tests", "e6": "tests", "smoke": "all"}
ALLOWED = {"PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "LANG", "LC_ALL"}


def clean_env():
    env = {k: v for k, v in os.environ.items() if k.upper() in ALLOWED}
    return {**env, "PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}


def run(files, run, timeout=600):
    with tempfile.TemporaryDirectory(prefix="rptg-") as tmp:
        root = Path(tmp)
        for path, text in files.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text, encoding="utf-8")
        try:
            proc = subprocess.run([sys.executable, "run_tests.py", WHAT[run]], cwd=root, env=clean_env(), capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=timeout)
            code, err, timed_out = proc.returncode, proc.stderr, False
        except subprocess.TimeoutExpired as e:
            code, err, timed_out = -1, e.stderr if isinstance(e.stderr, str) else "", True
        report = root / "report.json"
        data = json.loads(report.read_text(encoding="utf-8")) if report.exists() and not timed_out else None
    return {"exit_code": code, "timed_out": timed_out, "report": data, "stderr_tail": err[-2000:]}
