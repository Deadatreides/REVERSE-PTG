"""Окно rptg_host.gui: доступ только с токеном и своим Host; круг программы накладных через API окна —
запуск, вопрос утверждения, ответ, запуск до конца; назначение пишет project.yaml и проверяет оператора.

    python -m pytest tests/test_gui.py -q
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_host import FX, fake_send  # noqa: E402

from rptg_host import cli, gui, store  # noqa: E402


@pytest.fixture()
def window(tmp_path, monkeypatch):
    monkeypatch.setenv("RPTG_HOME", str(tmp_path / "home"))
    cli.main(["selftest"])
    examples = tmp_path / "examples.yaml"
    examples.write_text(yaml.safe_dump({k: [{"in": e["in"], "out": e["out"]} for e in v] for k, v in FX["s_new"]["user_examples"].items()},
                                       allow_unicode=True), encoding="utf-8")
    cli.main(["new", str(tmp_path / "app"), "--idea", FX["s_new"]["idea"], "--examples", str(examples)])
    server, app = gui.serve(store.Project(tmp_path / "app"), send=fake_send([]))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server, app
    server.shutdown()
    server.server_close()


def call(app, path, body=None, token=None, host=None):
    base = app.url.split("/#")[0]
    data = body if isinstance(body, bytes) else None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="GET" if body is None else "POST")
    req.add_header("X-Token", app.token if token is None else token)
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def state(app):
    return json.loads(call(app, "/api/state")[1])


def settle(app):
    for _ in range(600):
        s = state(app)
        if not s["running"]:
            return s
        time.sleep(0.5)
    raise AssertionError("круг не остановился")


def test_access_needs_token_and_own_host(window):
    """Как в PTG-MEM: токен во фрагменте адреса (на сервер не уходит), страница без данных — без токена, API —
    только с токеном; чужой Host — отказ всему."""
    _, app = window
    assert "/#t=" in app.url and "?" not in app.url
    assert call(app, "/api/state", token="wrong-token")[0] == 403
    assert call(app, "/api/state", token="")[0] == 403
    assert call(app, "/api/state", host="evil.example:80")[0] == 403
    assert call(app, "/", token="", host="evil.example:80")[0] == 403
    assert call(app, "/", token="")[0] == 200
    assert call(app, "/api/state")[0] == 200


def test_bad_requests_get_an_answer_not_a_dropped_connection(window):
    _, app = window
    assert call(app, "/api/answer", b"{not json")[0] == 400
    assert call(app, "/api/answer", {"type": "budget"})[0] == 400                   # нет limit
    assert json.loads(call(app, "/api/node?subject=nobody")[1])["card"] is None


def test_invoice_program_through_the_window(window):
    _, app = window
    assert call(app, "/api/run", {})[0] == 200
    s = settle(app)
    assert s["question"]["question"]["approve"] == "app" and s["status"]["phase"] == "MAP_REVIEW"
    assert {n["id"] for n in s["graph"]["nodes"]} == {"app", "app.billing", "app.money"}
    node = json.loads(call(app, "/api/node?subject=app")[1])
    assert node["card"]["id"] == "app" and "invoice" in node["flows"]
    assert call(app, "/api/answer", {"type": "approve"})[0] == 200
    assert call(app, "/api/answer", {"type": "approve"})[0] == 400                 # утверждать больше нечего
    call(app, "/api/run", {})
    s = settle(app)
    assert s["question"] == {"kind": "stop"} and s["status"]["phase"] == "DONE"
    assert {n["status"] for n in s["graph"]["nodes"]} == {"accepted"}


def test_assignment_goes_to_project_yaml_and_is_checked(window):
    _, app = window
    assert call(app, "/api/assign", {"mask": "app.billing.**", "role": "implementer", "operator": "sonnet"})[0] == 200
    cfg = yaml.safe_load((app.project.root / "project.yaml").read_text(encoding="utf-8"))
    assert cfg["overrides"]["app.billing.**"] == {"implementer": "sonnet"}
    assert call(app, "/api/assign", {"mask": "app", "role": "implementer", "operator": "нет-такого"})[0] == 400
    assert call(app, "/api/assign", {"mask": "app", "role": "architect", "operator": "opus"})[0] == 400
    before = (app.project.root / "project.yaml").read_bytes()
    for mask in ("level:2-3", "app..billing", "**", "app.billing.***"):       # ядро упало бы на каждом запуске
        assert call(app, "/api/assign", {"mask": mask, "role": "implementer", "operator": "sonnet"})[0] == 400, mask
    assert (app.project.root / "project.yaml").read_bytes() == before
    assert call(app, "/api/assign", {"mask": "level:2..3", "role": "designer", "operator": "opus"})[0] == 200


def test_calibration_table_comes_from_the_shell_file(window):
    """ARCHITECTURE §7: таблица компетенций — только по калибровке; её держит оболочка в ~/.rptg/competence.json."""
    _, app = window
    assert json.loads(call(app, "/api/table")[1]) == {"cells": [], "g0": False}
    table = {"cells": [{"operator": "haiku", "class": "compute", "n_fit": 6, "ok_fit": 5, "n_check": 6, "ok_check": 5,
                        "cost_per_success": "0.002", "low_data": False}], "g0": True}
    gui.store.write_atomic(gui.store.home() / "competence.json", json.dumps(table))
    assert json.loads(call(app, "/api/table")[1]) == table


def test_window_respects_the_project_lock(window):
    """Пока проект держит другой писатель (круг в командной строке), окно отвечает отказом, а круг окна
    встаёт с причиной — не перезаписывает чужой переход."""
    _, app = window
    with app.project.lock():
        status, body = call(app, "/api/answer", {"type": "pause"})
        assert status == 400 and "занят" in json.loads(body)["error"]
        assert call(app, "/api/run", {})[0] == 200
        s = settle(app)
    assert s["last"]["kind"] == "pause" and "занят" in s["last"]["reason"]
    assert call(app, "/api/answer", {"type": "pause"})[0] == 200
