# Rules for Claude: spend tokens only where they pay

Every turn of the main chat re-reads its whole context: about $0.08 on Opus. A Haiku worker turn costs about
$0.0002. The kit is cheap only if the expensive model wakes up rarely.

1. **The higher model is signalled only at the end.** The main chat wakes up when the run writes its result (done,
   blocked, approve, architect, env) or when the silence watcher fires. There are no intermediate signals.
2. **Launch, then stop.** Start `rptg_kit.run --detach` and the watcher it prints, as a background command, and end
   the turn. Until the watcher exits, make no calls:
   * do not poll the kit;
   * do not call `kit_status` between waves;
   * do not read `run-progress.log`, journals, `runs/` or the workers' code.
3. **Without the runner, waves only.** If subagents are dispatched by hand, launch the whole wave in the background.
   Do not read or answer the notifications of single subagents. Call `kit_next` again only after the whole wave has
   finished.
4. **The architect writes cards only.** No reference implementation and no leaf code. Work in a fresh chat with a
   small context, and do not re-read files the kit has already accepted.
5. **The kit runs the checks.** Models do not run pytest, mypy or other tools themselves. The only exception is the
   final `python -m pytest` after `done`.
6. **Workers answer in one line:** «принято» or «сдался: <why>».

The same rules are in the MCP server's instructions (`rptg_kit/server.py`), in the `develop` skill and in
[docs/KIT.en.md](docs/KIT.en.md).

---

# Правила для Claude: тратить токены только там, где они окупаются

Каждый ход главного чата — чтение всего его контекста, около $0,08 на Opus. Ход исполнителя Haiku стоит около
$0,0002. Kit дешев, только если дорогая модель просыпается редко.

1. **Вышестоящая модель получает сигнал только в конце.** Главный чат просыпается, когда прогон записал итог (done,
   blocked, approve, architect, env) или сработал сторож молчания. Промежуточных сигналов нет.
2. **Запустил и закончил ход.** Запустить `rptg_kit.run --detach` и сторожа, которого он печатает, фоновой командой,
   и закончить ход. До выхода сторожа — ни одного вызова:
   * kit не опрашивать;
   * `kit_status` между волнами не вызывать;
   * не читать `run-progress.log`, журналы, `runs/` и код исполнителей.
3. **Без раннера — только волнами.** Если субагентов запускает главный чат, вся волна идет в фоне. Уведомления
   отдельных субагентов не разбирать и на них не отвечать. Следующий `kit_next` — только когда закончилась вся волна.
4. **Архитектор пишет только карточки.** Без эталонной реализации и без кода листьев. Работает в свежем чате с малым
   контекстом и не перечитывает файлы, которые kit уже принял.
5. **Проверки гоняет kit.** Модели не запускают pytest, mypy и прочие инструменты сами. Исключение — итоговый
   `python -m pytest` после `done`.
6. **Исполнители отвечают одной строкой:** «принято» или «сдался: <почему>».

Те же правила — в подсказке сервера MCP (`rptg_kit/server.py`), в навыке `develop` и в [docs/KIT.md](docs/KIT.md).
