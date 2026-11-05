"""Поиск консольного claude раннером kit: приложение меняло папку (30.10: Claude-Data), прогон вне сеанса видит настоящие пути."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rptg_kit import run  # noqa: E402


def test_finds_claude_in_app_data_folder(tmp_path, monkeypatch):
    exe = tmp_path / "Claude-Data" / "claude_abc" / "claude-code" / "2.1.309" / "hash" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    monkeypatch.delenv("RPTG_CLAUDE", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "нет"))
    monkeypatch.setattr(run.shutil, "which", lambda name: None)
    assert run.claude_command() == [str(exe)]
