"""Сгенерированное не отстало от карты, а листья проходят статику Э1.

Обвязку пишет tools/codegen0.py; если разложение поправили, а обвязку не пересобрали, тесты
примеров гоняли бы старый код. Статика листьев — tools/leafcheck0.py: нарушение Э1 — провал.

    python -m pytest tests/test_generated.py -q
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          env={"PYTHONIOENCODING": "utf-8", "SYSTEMROOT": "C:\\Windows", "PATH": ""})


def test_wiring_is_up_to_date():
    done = run("tools/codegen0.py", "rptg.lang", "--check")
    assert done.returncode == 0, done.stdout + done.stderr


def test_leaves_pass_static_checks():
    done = run("tools/leafcheck0.py")
    assert done.returncode == 0, done.stdout + done.stderr
