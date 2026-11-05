"""Запуск сервера MCP rptg kit: `<.venv-kit>/python <REVERSE-PTG>/rptg_kit/serve.py` (stdio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rptg_kit.server import main  # noqa: E402

main()
