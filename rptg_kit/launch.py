"""Start the kit's MCP server with the right Python, so plugin.json needs no machine paths.

Which kit folder: the one named in ~/.rptg-kit/home (a working checkout you edit), else the plugin's own folder.
Which Python: RPTG_KIT_PYTHON, else the folder's .venv-kit, else the Python that runs this file.
The server talks MCP over stdio; the child inherits it, and this process only waits for it.
"""
import os
import subprocess
import sys
from pathlib import Path


def kit_home() -> Path:
    mark = Path.home() / ".rptg-kit" / "home"
    if mark.exists():
        home = Path(mark.read_text(encoding="utf-8").strip())
        if (home / "rptg_kit" / "serve.py").exists():
            return home
    return Path(__file__).resolve().parent.parent


def kit_python(home: Path) -> str:
    env = os.environ.get("RPTG_KIT_PYTHON")
    if env and Path(env).exists():
        return env
    for rel in (("Scripts", "python.exe"), ("bin", "python")):
        exe = home / ".venv-kit" / Path(*rel)
        if exe.exists():
            return str(exe)
    return sys.executable


def main() -> int:
    home = kit_home()
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.call([kit_python(home), str(home / "rptg_kit" / "serve.py")], env=env)


if __name__ == "__main__":
    sys.exit(main())
