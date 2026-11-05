"""Подключить rptg kit к папке проекта Claude Code — «подключи сервер из этой папки».

    <REVERSE-PTG>\\.venv-kit\\Scripts\\python.exe <REVERSE-PTG>\\rptg_kit\\connect.py <папка проекта>

Пишет в папку проекта .mcp.json (сервер rptg; другие серверы файла не трогает) и роли субагентов в
.claude/agents/ (rptg-designer — sonnet, rptg-implementer — haiku). Ключей и секретов не пишет. Claude Code спросит
разрешение на сервер, когда чат в этой папке запустится снова.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PYTHON = ROOT / ".venv-kit" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def server_entry():
    return {"command": str(PYTHON), "args": [str(HERE / "serve.py")], "env": {"PYTHONUTF8": "1"}, "timeout": 1800000}


def connect(target):
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    mcp = target / ".mcp.json"
    data = json.loads(mcp.read_text(encoding="utf-8")) if mcp.exists() else {}
    data.setdefault("mcpServers", {})["rptg"] = server_entry()
    mcp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    agents = target / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    copied = []
    for f in sorted((ROOT / "agents").glob("rptg-*.md")):
        shutil.copy2(f, agents / f.name)
        copied.append(f.name)
    return mcp, agents, copied


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("укажите папку проекта: connect.py <папка>")
    if not PYTHON.exists():
        sys.exit(f"нет окружения с готовыми проверками: {PYTHON}")
    mcp_file, agents_dir, names = connect(sys.argv[1])
    print(f"сервер rptg прописан: {mcp_file}\nроли: {agents_dir} ({', '.join(names)})\n"
          "перезапустите чат в этой папке, разрешите сервер rptg и скажите: «разработай ПО по ТЗ <файл>»")
