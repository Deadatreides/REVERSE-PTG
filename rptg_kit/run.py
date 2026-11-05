"""Прогон волн без главного чата: kit сам запускает исполнителей и проектировщиков.

Каждый билет — отдельный консольный Claude Code (`claude -p`):
* модель — из билета (лестница haiku → sonnet → opus);
* роль — текст agents/<роль>.md;
* инструменты — только kit (kit_brief, kit_submit, kit_guide, kit_status) и чтение файлов;
* хуки выключены, сеанс на диск не пишется — память проекта не засоряется сеансами исполнителей.

Главный чат вызывает прогон один раз (фоновая команда) и получает одно уведомление — итог: что дальше нужно от него
(architect, approve, blocked, env, done) и сколько стоили исполнители. Уведомления каждого исполнителя в главный
чат больше не приходят: 12.10 они стоили $6,58 из $11,93 главного чата.

Запуск:  python -m rptg_kit.run <папка проекта> [--parallel 6] [--timeout 3600]
Консольный claude: RPTG_CLAUDE (путь или JSON-список команды), иначе claude из PATH, иначе последняя версия
из %APPDATA%/Claude/claude-code. Он должен быть авторизован (один раз: `claude`, затем /login).
"""
import argparse
import concurrent.futures
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import server

PLUGIN = Path(__file__).resolve().parent.parent
ROLE_TOOLS = ["mcp__rptg__kit_brief", "mcp__rptg__kit_submit", "mcp__rptg__kit_guide", "mcp__rptg__kit_status"]
READ_TOOLS = ["Read", "Grep", "Glob"]
DISPATCHES = 3  # сколько раз прогон выдаёт один билет, если исполнитель ушёл, не исчерпав сдач


def claude_command():
    env = os.environ.get("RPTG_CLAUDE")
    if env:
        return json.loads(env) if env.lstrip().startswith("[") else [env]
    found = shutil.which("claude")
    if found:
        return [found]
    # Приложение Claude — пакет MSIX: его %APPDATA%\Claude видно только процессам пакета, а прогону, запущенному вне
    # сеанса (WMI), — настоящая папка в Packages (17.10); с версии 4.4 приложение держит её в Claude-Data (30.10).
    apps = sorted(glob.glob(os.path.expandvars(r"%APPDATA%\Claude\claude-code\*\*\claude.exe"))
                  + glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code\*\*\claude.exe"))
                  + glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Claude-Data\claude_*\claude-code\*\*\claude.exe")),
                  key=os.path.getmtime)
    if apps:
        return [apps[-1]]
    raise FileNotFoundError("нет консольного claude: задайте RPTG_CLAUDE")


def role_prompt(agent):
    text = (PLUGIN / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def mcp_config():
    serve = Path(__file__).with_name("serve.py")
    return json.dumps({"mcpServers": {"rptg": {"command": sys.executable, "args": [str(serve)], "env": {"PYTHONUTF8": "1"}}}})


def worker_command(ticket):
    return [*claude_command(), "-p", ticket["dispatch"], "--model", ticket["model"], "--output-format", "json",
            "--append-system-prompt", role_prompt(ticket["agent"]),
            "--mcp-config", mcp_config(), "--strict-mcp-config",
            "--tools", ",".join(READ_TOOLS), "--allowedTools", ",".join(ROLE_TOOLS + READ_TOOLS),
            "--settings", json.dumps({"disableAllHooks": True}), "--no-session-persistence"]


def run_worker(ticket, log_dir, timeout):
    """Один исполнитель; итог и цена — в .rptg-kit/runs/<билет>-<время>.json."""
    started = time.time()
    try:
        proc = subprocess.run(worker_command(ticket), cwd=log_dir, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, env={**os.environ, "PYTHONUTF8": "1"})
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        out, err = e.stdout or "", f"тайм-аут {timeout} с"
    except OSError as e:
        out, err = "", str(e)
    try:
        res = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        res = {"result": (out or err)[-1500:], "is_error": True}
    record = {"ticket": ticket["ticket"], "kind": ticket["kind"], "target": ticket["target"], "model": ticket["model"],
              "seconds": round(time.time() - started), "error": bool(res.get("is_error")),
              "result": str(res.get("result") or "")[-600:], "cost_usd": res.get("total_cost_usd") or 0.0,
              "usage": res.get("usage"), "model_usage": res.get("modelUsage"), "stderr": (err or "")[-600:]}
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (log_dir / f"{ticket['ticket']}-{stamp}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    # строка хода на каждого исполнителя: сторож меряет тишину по одному исполнителю, а не по самой долгой волне
    progress(log_dir.parent.parent, f"{ticket['ticket']} {ticket['target']} {ticket['model']}: {record['seconds']} с, "
                                    f"{record['result'][:60]!r}")
    return record


def progress(project_dir, line):
    """Ход прогона — строка на волну в .rptg-kit/run-progress.log: по времени последней строки видно, идёт ли работа,
    без опроса kit главным чатом."""
    path = Path(project_dir) / ".rptg-kit" / "run-progress.log"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%d.%m %H:%M:%S')}  {line}\n")


def notify(project_dir, result):
    """Итог прогона — последней строкой хода; её и появление итога в run.log ждёт сторож главного чата (watch)."""
    text = f"{result.get('say') or ''} принято {result['accepted']}, ${result['cost_usd']:.2f}".strip()
    progress(project_dir, f"итог: {result['kind']} — {text}")


WATCH = """d='{kit}'; s=$(date +%s); until grep -q '"kind"' "$d/run.log" 2>/dev/null; do \
p=$(stat -c %Y "$d/run-progress.log" 2>/dev/null || echo $s); [ $(( $(date +%s) - p )) -gt {stale} ] && \
{{ echo "ЗАВИС: ход молчит дольше {mins} мин — дольше самого долгого исполнителя"; break; }}; sleep 30; done; tail -n 4 "$d/run-progress.log"; head -c 1500 "$d/run.log\""""


LONGEST_SECONDS = 1423  # самый долгий исполнитель на 18.10: 167 работавших во всех проектах, медиана 92 с, p90 460 с


def stale_seconds(project_dir, poll=60):
    """Тишина, после которой прогон считается зависшим: самый долгий работавший исполнитель проекта (по журналу
    runs/) плюс пауза раннера между опросами. Записей меньше 20 — замер 18.10 по всем проектам."""
    seconds = []
    for f in (Path(project_dir) / ".rptg-kit" / "runs").glob("*.json"):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not r.get("error") and r.get("cost_usd"):
            seconds.append(int(r.get("seconds") or 0))
    longest = max(seconds) if len(seconds) >= 20 else LONGEST_SECONDS
    return longest + poll


def watch_command(project_dir, stale=None):
    """Сторож для главного чата (Bash, run_in_background): выходит, когда прогон записал итог (done, blocked,
    architect, approve, env, work — билеты крутятся, лимит) или когда ход молчит дольше самого долгого исполнителя
    (завис); выход будит главный чат сразу (18.10: пользователь сам угадывал, что прогон стоит, и звал главный чат)."""
    stale = stale or stale_seconds(project_dir)
    kit = str(Path(project_dir).resolve() / ".rptg-kit").replace("\\", "/")
    return WATCH.format(kit=kit, stale=stale, mins=round(stale / 60))


def run(project_dir, parallel=6, timeout=3600, poll=60):
    log_dir = Path(project_dir) / ".rptg-kit" / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    dispatched, records = {}, []
    while True:
        answer = server.kit_next(project_dir, limit=parallel)
        if answer["kind"] != "work":
            break
        tickets = [t for t in answer.get("tickets") or [] if dispatched.get(t["ticket"], 0) < DISPATCHES]
        if not tickets:
            if answer.get("in_progress"):
                time.sleep(poll)  # билеты на руках у других исполнителей
                continue
            break
        for t in tickets:
            dispatched[t["ticket"]] = dispatched.get(t["ticket"], 0) + 1
        with concurrent.futures.ThreadPoolExecutor(len(tickets)) as pool:
            done = list(pool.map(lambda t: run_worker(t, log_dir, timeout), tickets))
        records += done
        for r in done:  # сдался, не исчерпав сдач, — ступень неудачна (flow.give_up); иначе билет крутится на месте
            if r["result"].lstrip().lower().startswith("сдался"):
                server.give_up(project_dir, r["ticket"], r["result"])
        server.release(project_dir, [r["ticket"] for r in done])  # ушёл, не исчерпав сдач, — билет снова свободен
        progress(project_dir, f"волна: {len(done)} исполн., принято {sum('принято' in r['result'] for r in done)}, "
                              f"сдались {sum(r['result'].lstrip().lower().startswith('сдался') for r in done)}, "
                              f"упали {sum(r['error'] for r in done)}, ${sum(r['cost_usd'] for r in done):.2f}")
        if all(r["error"] for r in done):
            answer = {"kind": "workers", "say": "все исполнители волны упали — см. records (авторизация claude? окружение?)"}
            break
    cost = sum(r["cost_usd"] for r in records)
    by_model = {}
    for r in records:
        by_model[r["model"]] = round(by_model.get(r["model"], 0.0) + r["cost_usd"], 4)
    return {"kind": answer["kind"], "say": answer.get("say") or answer.get("reason", ""), "workers": len(records),
            "accepted": sum("принято" in r["result"] for r in records), "cost_usd": round(cost, 4), "by_model": by_model,
            "failed": [{k: r[k] for k in ("ticket", "target", "model", "result", "stderr")} for r in records if r["error"]][:8],
            "summary": answer.get("summary", "")}


def detach(project_dir, parallel, timeout):
    """Запуск прогона процессом вне сеанса: дочерние процессы сеанса настольного приложения (и Start-Process тоже)
    гибнут при его перезапуске — 16.10 прогон умер молча с пустыми журналами. Win32_Process.Create (WMI) порождает
    процесс вне группы сеанса. Прежний run.log уходит в run-<время>.log. Ответ — PID или ошибка."""
    kit = Path(project_dir).resolve() / ".rptg-kit"
    log, err = kit / "run.log", kit / "run.err"
    if log.exists():
        log.rename(kit / f"run-{time.strftime('%Y%m%dT%H%M%S')}.log")
    line = (f'cmd.exe /c set PYTHONUTF8=1&& "{sys.executable}" -m rptg_kit.run "{Path(project_dir).resolve()}" '
            f'--parallel {parallel} --timeout {timeout} > "{log}" 2> "{err}"')
    ps = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
          "@{CommandLine = $env:RPTG_LINE; CurrentDirectory = $env:RPTG_CWD}; \"$($r.ReturnValue) $($r.ProcessId)\"")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True,
                         text=True, env={**os.environ, "RPTG_LINE": line, "RPTG_CWD": str(PLUGIN)}, timeout=60)
    code, _, pid = out.stdout.strip().partition(" ")
    if code != "0":
        return f"не запущен: {out.stdout.strip()} {out.stderr.strip()[-300:]}"
    return (f"прогон запущен вне сеанса, PID {pid}; журнал {log}, ход — {kit / 'run-progress.log'}\n"
            f"сторож (Bash, run_in_background):\n{watch_command(project_dir)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--detach", action="store_true",
                    help="перезапуститься вне сеанса Claude Code (WMI) с журналами .rptg-kit/run.log и run.err")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.detach:
        print(detach(a.project_dir, a.parallel, a.timeout))
        return
    progress(a.project_dir, "старт прогона")
    result = run(a.project_dir, a.parallel, a.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=1), flush=True)
    notify(a.project_dir, result)


if __name__ == "__main__":
    main()
