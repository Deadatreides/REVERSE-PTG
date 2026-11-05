"""Окно rptg (ARCHITECTURE §7): локальный сервер на 127.0.0.1, доступ по токену — как в PTG-MEM.

Страница — gui.html (без внешних зависимостей и без данных) — отдаётся без токена; токен — во фрагменте
адреса (`#t=…`: фрагмент не уходит на сервер и в историю запросов), API — JSON с токеном в заголовке
X-Token. Заголовок Host проверяется у всех запросов — от подмены DNS. Окно только читает состояние и
отправляет события ядру тем же путём, что команды: состояние меняет только apply_event. Круг идёт в
отдельном потоке и останавливается между шагами; писатель состояния один (замок проекта, store.lock).
"""
import http.server
import json
import secrets
import threading
import urllib.parse
from pathlib import Path

from . import llm, loop, store

PAGE = Path(__file__).with_name("gui.html")
EVENTS = {
    "approve": lambda b, q: {"kind": "user_answered", "reply": {**q, "decision": "yes", "comment": ""}},
    "reject": lambda b, q: {"kind": "user_answered", "reply": {**q, "decision": "no", "comment": b.get("comment", "")}},
    "decide": lambda b, q: {"kind": "user_answered", "reply": {"decide": b["subject"], "decision": b["decision"], "comment": b.get("comment", "")}},
    "recheck": lambda b, q: {"kind": "user_answered", "reply": {"recheck": b["subject"]}},
    "pause": lambda b, q: {"kind": "command", "reply": {"command": "pause"}},
    "resume": lambda b, q: {"kind": "command", "reply": {"command": "resume"}},
    "budget": lambda b, q: {"kind": "command", "reply": {"command": "budget", "limit": b["limit"]}},
}


class App:
    def __init__(self, project, send=llm.send):
        self.project, self.send, self.token = project, send, secrets.token_urlsafe(24)
        self.thread, self.halt, self.log, self.last = None, False, [], None
        self.mutex = threading.Lock()

    def core(self):
        return loop.Core(self.project.config(), self.project.table())

    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def snapshot(self):
        core, state = self.core(), self.project.load_state()
        return {"status": core.view(state, kind="status")["data"], "graph": core.view(state, kind="graph")["data"],
                "question": None if self.running() else core.next(state), "running": self.running(), "log": self.log[-30:],
                "last": self.last, "operators": sorted(self.project.config()["operators"])}

    def node(self, subject):
        core, state = self.core(), self.project.load_state()
        data = core.view(state, kind="node", subject=subject)["data"]
        return {**data, "flows": (state["designs"].get(subject) or {}).get("flows", {})}

    def answer(self, body):
        with self.mutex:
            if self.running():
                raise ValueError("круг идёт — сначала остановите")
            with self.project.lock():
                core = self.core()
                question = core.next(self.project.load_state()).get("question") or {}
                if body["type"] in ("approve", "reject") and "approve" not in question:
                    raise ValueError("нечего утверждать")
                loop.apply(self.project, core, self.project.load_state(), EVENTS[body["type"]](body, question))

    def run(self):
        with self.mutex:
            if self.running():
                raise ValueError("круг уже идёт")
            self.halt, self.log = False, []

            def work():
                try:
                    with self.project.lock():
                        self.last = loop.run(self.project, send=self.send, say=self.log.append, stop=lambda: self.halt)
                except Exception as e:  # замок занят или сбой ядра — причина видна в окне, а не теряется с потоком
                    self.last = {"kind": "pause", "reason": f"{type(e).__name__}: {e}"}
            self.thread = threading.Thread(target=work, daemon=True)
            self.thread.start()

    def assign(self, body):
        """Ручное назначение (LOGIC §6.6) — то же, что `rptg assign` (store.assign)."""
        with self.mutex:
            store.assign(self.project.root, body["mask"], body["role"], body["operator"])


def handler(app, port):
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body, kind="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def route(self, method):
            if self.headers.get("Host") not in hosts:
                return self.reply(403, {"error": "чужой Host"})
            url = urllib.parse.urlparse(self.path)
            if method == "GET" and url.path == "/":
                return self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if not secrets.compare_digest(self.headers.get("X-Token") or "", app.token):
                return self.reply(403, {"error": "нет доступа"})
            query = dict(urllib.parse.parse_qsl(url.query))
            gets = {"/api/state": app.snapshot, "/api/node": lambda: app.node(query.get("subject", "")),
                    "/api/outcomes": lambda: app.core().view(app.project.load_state(), kind="competence")["data"],
                    "/api/table": app.project.table}
            posts = {"/api/answer": lambda b: app.answer(b), "/api/run": lambda b: app.run(),
                     "/api/stop": lambda b: setattr(app, "halt", True), "/api/assign": lambda b: app.assign(b)}
            routes = gets if method == "GET" else posts
            if url.path not in routes:
                return self.reply(404, {"error": "нет такого"})
            try:
                if method == "GET":
                    return self.reply(200, routes[url.path]())
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                routes[url.path](body)
                return self.reply(200, {"ok": True})
            except (ValueError, KeyError, store.Busy) as e:
                return self.reply(400, {"error": str(e)})
            except Exception as e:  # сбой ядра или файла — ответ с причиной, а не оборванное соединение
                return self.reply(500, {"error": f"{type(e).__name__}: {e}"})

        def do_GET(self):
            self.route("GET")

        def do_POST(self):
            self.route("POST")

    return Handler


def serve(project, port=0, send=llm.send):
    """Сервер на 127.0.0.1; port 0 — свободный. Возвращает сервер и приложение (адрес с токеном — url)."""
    app = App(project, send)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), None)
    server.RequestHandlerClass = handler(app, server.server_address[1])
    app.url = f"http://127.0.0.1:{server.server_address[1]}/#t={app.token}"
    return server, app
