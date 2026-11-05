# Самопроверка карты rptg

Сгенерировано `tools/selfcheck.py`. Это прототип проверок, а не rptg: П4 и П5 здесь —
заглушка (совпадение условий после подстановки), настоящие доказательства даст Z3.
Контрольные случаи прототипа четырёх видов — `tools/selfcheck_cases.py`.

**Итог: нарушений нет.**

| что | сколько |
|---|---|
| разложений (корень и ниже) | 23 |
| типов | 215 |
| операций | 207 |
| условий, разобрано CL | 328 |
| примеров | 479 (точных 332, по подмножеству 147) |
| гарантий, вычисленных на точных примерах | 529 |
| обязательств П4 доказано заглушкой | 45 из 53 |
| гарантий П5 выведено заглушкой | 117 из 132 |

## Маршрутизация узлов

Вид узла — LOGIC §6.2, прикидка — §6.5 (S_раз для составных, S_исп для финальных),
назначения — `design/project.yaml`.

| узел | уровень | вид | правило | операций | est_lines | uses | прикидка | оператор | почему |
|---|---|---|---|---|---|---|---|---|---|
| `rptg.lang` | 2 | составной | 4 | 13 | 1500 | — | 68 | opus | ручное |
| `rptg.check` | 2 | составной | 3 | 8 | 1600 | lang | 71 | opus | ручное |
| `rptg.plan` | 2 | составной | 3 | 4 | 1200 | check, lang, talk | 64 | opus | ручное |
| `rptg.talk` | 2 | составной | 3 | 4 | 700 | lang | 44 | opus | ручное |
| `rptg.build` | 2 | составной | 3 | 1 | 900 | lang | 37 | opus | ручное |
| `rptg.bench` | 2 | составной | 3 | 2 | 250 | lang | 32 | opus | ручное |
| `rptg.views` | 2 | составной | 3 | 1 | 400 | check, lang | 26 | opus | ручное |
| `rptg.bench.split` | 3 | финальный | 7 | 1 | 30 | — | 37 | mini | прикидка |
| `rptg.bench.tasks` | 3 | финальный | 7 | 1 | 25 | — | 39 | mini | прикидка |
| `rptg.bench.tally` | 3 | финальный | 7 | 1 | 50 | — | 59 | gemini | прикидка |
| `rptg.bench.price` | 3 | финальный | 7 | 1 | 45 | — | 49 | mini | прикидка |
| `rptg.bench.gate` | 3 | финальный | 7 | 1 | 45 | — | 26 | gguf | прикидка |
| `rptg.build.plan` | 3 | финальный | 7 | 2 | 110 | — | 48 | mini | прикидка |
| `rptg.build.conds` | 3 | финальный | 7 | 2 | 40 | — | 26 | gguf | прикидка |
| `rptg.build.types` | 3 | финальный | 7 | 2 | 100 | — | 40 | mini | прикидка |
| `rptg.build.wrap` | 3 | финальный | 7 | 1 | 40 | — | 34 | mini | прикидка |
| `rptg.build.flows` | 3 | финальный | 7 | 4 | 150 | — | 32 | mini | прикидка |
| `rptg.build.modules` | 3 | финальный | 7 | 3 | 120 | — | 35 | mini | прикидка |
| `rptg.build.assemble` | 3 | финальный | 7 | 1 | 20 | — | 21 | gguf | прикидка |
| `rptg.check.answer.raw` | 4 | финальный | 7 | 1 | 60 | — | 44 | mini | прикидка |
| `rptg.check.answer.shape` | 4 | финальный | 7 | 1 | 35 | — | 24 | gguf | прикидка |
| `rptg.check.answer.conds` | 4 | финальный | 7 | 1 | 45 | — | 28 | gguf | прикидка |
| `rptg.check.answer.names` | 4 | финальный | 7 | 1 | 60 | — | 33 | mini | прикидка |
| `rptg.check.answer.judge` | 4 | финальный | 7 | 1 | 45 | — | 46 | mini | прикидка |
| `rptg.check.code.rules` | 4 | финальный | 7 | 1 | 55 | — | 29 | gguf | прикидка |
| `rptg.check.code.size` | 4 | финальный | 7 | 1 | 55 | — | 39 | mini | прикидка |
| `rptg.check.code.outcome` | 4 | финальный | 7 | 1 | 20 | — | 26 | gguf | прикидка |
| `rptg.check.code.runs` | 4 | финальный | 7 | 1 | 60 | — | 51 | mini | прикидка |
| `rptg.check.contract.data.edges` | 5 | финальный | 7 | 1 | 60 | — | 49 | mini | прикидка |
| `rptg.check.contract.data.subs` | 5 | финальный | 7 | 1 | 30 | — | 30 | mini | прикидка |
| `rptg.check.contract.data.outcome` | 5 | финальный | 7 | 1 | 30 | — | 41 | mini | прикидка |
| `rptg.check.contract.examples.samples` | 5 | финальный | 7 | 1 | 55 | — | 39 | mini | прикидка |
| `rptg.check.contract.examples.outcome` | 5 | финальный | 7 | 1 | 25 | — | 37 | mini | прикидка |
| `rptg.check.contract.logic.facts` | 5 | финальный | 5 | 1 | 110 | — | 46 | mini | прикидка, вид — ручной |
| `rptg.check.contract.logic.equal` | 5 | финальный | 7 | 1 | 45 | — | 47 | mini | прикидка |
| `rptg.check.contract.logic.feasible` | 5 | финальный | 7 | 1 | 35 | — | 28 | gguf | прикидка |
| `rptg.check.contract.logic.render` | 5 | финальный | 7 | 1 | 45 | — | 47 | mini | прикидка |
| `rptg.check.contract.logic.outcome` | 5 | финальный | 7 | 1 | 45 | — | 50 | mini | прикидка |
| `rptg.check.contract.data` | 4 | составной | 3 | 1 | 150 | lang | 14 | gemini | прикидка |
| `rptg.check.contract.logic` | 4 | составной | 3 | 1 | 330 | lang | 26 | gemini | прикидка |
| `rptg.check.contract.examples` | 4 | составной | 3 | 1 | 100 | lang | 12 | gemini | прикидка |
| `rptg.check.graph.tree` | 4 | финальный | 7 | 1 | 60 | — | 41 | mini | прикидка |
| `rptg.check.graph.links` | 4 | финальный | 7 | 1 | 60 | — | 34 | mini | прикидка |
| `rptg.check.graph.outcome` | 4 | финальный | 7 | 1 | 20 | — | 30 | mini | прикидка |
| `rptg.check.graph.reach` | 4 | финальный | 7 | 1 | 35 | — | 16 | gguf | прикидка |
| `rptg.check.graph.impact` | 4 | финальный | 7 | 1 | 40 | — | 19 | gguf | прикидка |
| `rptg.check.verdict.applied` | 4 | финальный | 7 | 1 | 35 | — | 22 | gguf | прикидка |
| `rptg.check.verdict.content` | 4 | финальный | 7 | 1 | 60 | — | 32 | mini | прикидка |
| `rptg.check.verdict.order` | 4 | финальный | 7 | 1 | 25 | — | 43 | mini | прикидка |
| `rptg.check.verdict.accept` | 4 | финальный | 7 | 1 | 35 | — | 26 | gguf | прикидка |
| `rptg.check.verdict.report` | 4 | финальный | 7 | 1 | 40 | — | 28 | gguf | прикидка |
| `rptg.check.answer` | 3 | составной | 3 | 2 | 240 | lang | 30 | gemini | прикидка |
| `rptg.check.graph` | 3 | составной | 6 | 3 | 350 | — | 29 | gemini | прикидка |
| `rptg.check.contract` | 3 | составной | 3 | 3 | 450 | lang | 39 | gemini | прикидка |
| `rptg.check.code` | 3 | составной | 6 | 2 | 300 | — | 28 | gemini | прикидка |
| `rptg.check.verdict` | 3 | составной | 3 | 4 | 240 | lang | 38 | gemini | прикидка |
| `rptg.check.cases` | 3 | финальный | 7 | 3 | 90 | — | 33 | mini | прикидка |
| `rptg.lang.cl.logic.smt` | 5 | финальный | 5 | 1 | 200 | — | 48 | mini | прикидка, вид — ручной |
| `rptg.lang.cl.logic.schema` | 5 | финальный | 5 | 1 | 90 | — | 42 | mini | прикидка, вид — ручной |
| `rptg.lang.cl.logic.script` | 5 | финальный | 7 | 2 | 50 | — | 32 | mini | прикидка |
| `rptg.lang.cl.logic.solve` | 5 | финальный | 7 | 1 | 60 | — | 37 | mini | прикидка |
| `rptg.lang.cl.logic.decode` | 5 | финальный | 7 | 2 | 40 | — | 25 | gguf | прикидка |
| `rptg.lang.cl.strategy.bounds` | 5 | финальный | 7 | 1 | 50 | — | 36 | mini | прикидка |
| `rptg.lang.cl.strategy.gen` | 5 | финальный | 7 | 1 | 60 | — | 33 | mini | прикидка |
| `rptg.lang.cl.parse` | 4 | финальный | 5 | 1 | 180 | — | 37 | mini | прикидка, вид — ручной |
| `rptg.lang.cl.typecheck` | 4 | финальный | 5 | 1 | 200 | — | 46 | mini | прикидка, вид — ручной |
| `rptg.lang.cl.measure` | 4 | финальный | 7 | 1 | 40 | — | 26 | gguf | прикидка |
| `rptg.lang.cl.evaluate` | 4 | финальный | 5 | 1 | 150 | — | 35 | mini | прикидка, вид — ручной |
| `rptg.lang.cl.python` | 4 | финальный | 5 | 1 | 120 | — | 33 | mini | прикидка, вид — ручной |
| `rptg.lang.cl.logic` | 4 | составной | 6 | 2 | 300 | — | 26 | gemini | прикидка |
| `rptg.lang.cl.strategy` | 4 | составной | 6 | 1 | 110 | — | 8 | gemini | прикидка |
| `rptg.lang.cl` | 3 | составной | 6 | 6 | 1050 | — | 56 | grok | прикидка |
| `rptg.lang.types` | 3 | финальный | 7 | 5 | 280 | — | 32 | mini | прикидка |
| `rptg.lang.canon` | 3 | финальный | 7 | 2 | 80 | — | 18 | gguf | прикидка |
| `rptg.plan.choose.pending` | 4 | финальный | 7 | 2 | 90 | — | 46 | mini | прикидка |
| `rptg.plan.machine.intake` | 4 | финальный | 7 | 4 | 190 | — | 39 | mini | прикидка |
| `rptg.plan.machine.policy` | 4 | финальный | 7 | 3 | 170 | — | 48 | mini | прикидка |
| `rptg.plan.machine.element` | 4 | финальный | 7 | 3 | 105 | — | 34 | mini | прикидка |
| `rptg.plan.machine.settle` | 4 | финальный | 7 | 4 | 110 | — | 31 | mini | прикидка |
| `rptg.plan.machine.refresh` | 4 | составной | 4 | 7 | 200 | — | 43 | gemini | прикидка |
| `rptg.plan.machine.close` | 4 | финальный | 7 | 2 | 100 | — | 38 | mini | прикидка |
| `rptg.plan.route.measure` | 4 | финальный | 7 | 2 | 35 | — | 18 | gguf | прикидка |
| `rptg.plan.route.prior` | 4 | финальный | 7 | 2 | 55 | — | 41 | mini | прикидка |
| `rptg.plan.route.masks` | 4 | финальный | 7 | 1 | 25 | — | 27 | gguf | прикидка |
| `rptg.plan.route.decide` | 4 | финальный | 7 | 2 | 55 | — | 33 | mini | прикидка |
| `rptg.plan.route.kind` | 4 | финальный | 7 | 2 | 35 | — | 28 | gguf | прикидка |
| `rptg.plan.queue` | 3 | финальный | 7 | 1 | 45 | — | 41 | mini | прикидка |
| `rptg.plan.route` | 3 | составной | 3 | 5 | 260 | lang | 39 | gemini | прикидка |
| `rptg.plan.machine` | 3 | составной | 3 | 6 | 700 | check, lang, talk, route | 61 | grok | прикидка |
| `rptg.plan.choose` | 3 | составной | 3 | 1 | 110 | lang, machine | 25 | gemini | прикидка |
| `rptg.talk.context.idea` | 4 | финальный | 7 | 1 | 15 | — | 24 | gguf | прикидка |
| `rptg.talk.context.branch` | 4 | финальный | 7 | 1 | 60 | — | 56 | gemini | прикидка |
| `rptg.talk.context.leaf` | 4 | финальный | 7 | 1 | 45 | — | 38 | mini | прикидка |
| `rptg.talk.context.repair` | 4 | финальный | 7 | 1 | 12 | — | 16 | gguf | прикидка |
| `rptg.talk.context.merge` | 4 | финальный | 7 | 1 | 12 | — | 21 | gguf | прикидка |
| `rptg.talk.context` | 3 | составной | 6 | 1 | 150 | — | 20 | gemini | прикидка |
| `rptg.talk.schema` | 3 | финальный | 7 | 1 | 45 | — | 32 | mini | прикидка |
| `rptg.talk.text` | 3 | финальный | 7 | 1 | 50 | — | 44 | mini | прикидка |
| `rptg.talk.wire` | 3 | финальный | 7 | 3 | 150 | — | 45 | mini | прикидка |
| `rptg.talk.price` | 3 | финальный | 7 | 1 | 35 | — | 25 | gguf | прикидка |
| `rptg.views.status` | 3 | финальный | 7 | 1 | 15 | — | 8 | gguf | прикидка |
| `rptg.views.node` | 3 | финальный | 7 | 2 | 40 | — | 17 | gguf | прикидка |
| `rptg.views.graph` | 3 | финальный | 7 | 2 | 45 | — | 12 | gguf | прикидка |
| `rptg.views.outcomes` | 3 | финальный | 7 | 1 | 30 | — | 15 | gguf | прикидка |
| `rptg.views.pick` | 3 | финальный | 7 | 1 | 10 | — | 9 | gguf | прикидка |

## Что заглушка П4/П5 не вывела — ждёт Z3

* `rptg.bench.plan.n3`: «forall i in reference.items: len(i.card.ops) == 1» → `(forall i in reference.items: (len(i.card.ops) == 1))`
* `rptg.bench.table.n2`: «tally.ok_fit <= tally.n_fit and tally.ok_check <= tally.n_check» — поэлементно, нужен Z3
* `rptg.bench.table.n2`: «len(tally.costs) == tally.n_fit + tally.n_check» — поэлементно, нужен Z3
* `rptg.bench.table.n2`: «forall c in tally.costs: c >= 0» — поэлементно, нужен Z3
* `rptg.plan.machine.absorb.n2`: «evidence.verdict == "fail"» — поэлементно, нужен Z3
* `rptg.plan.machine.recheck.n7`: «event.kind == "model_answered" => event.task != null and event.answer != null» — поэлементно, нужен Z3
* `rptg.plan.machine.recheck.n7`: «event.kind == "sandbox_finished" => event.target != null and event.output != null» — поэлементно, нужен Z3
* `rptg.plan.machine.recheck.n10`: «evidence.verdict == "fail"» — поэлементно, нужен Z3
* `rptg.bench.table`: «forall c in result.cells: c.ok_fit <= c.n_fit and c.ok_check <= c.n_check»
* `rptg.bench.table`: «forall c in result.cells: c.low_data == (c.n_fit + c.n_check < cfg.routing.n_min)»
* `rptg.check.verdict.subject`: «result.subject == answer.subject or answer.kind == "none"»
* `rptg.check.verdict.accepted`: «result.accepted => len(result.missing) == 0»
* `rptg.lang.cl.logic.sat`: «forall i in result.core: i >= 0 and i < len(conds)»
* `rptg.lang.cl.sat`: «forall i in result.core: i >= 0 and i < len(conds)»
* `rptg.plan.choose.action`: «state.phase == "DONE" => result.kind == "stop"»
* `rptg.plan.choose.action`: «state.phase == "MAP_REVIEW" => result.kind == "ask_user"»
* `rptg.plan.machine.close`: «len(result.journal) >= 1»
* `rptg.plan.machine.close`: «forall e in result.evidence: e.hard»
* `rptg.talk.context.facts`: «task.kind == "map" => forall s in result.sections: s.key in {"idea", "examples", "report"}»
* `rptg.talk.context.facts`: «task.kind == "function" => forall s in result.sections: s.key in {"op", "purpose", "types", "imports", "limits", "report"}»
* `rptg.talk.context.facts`: «task.kind != "revision" => forall s in result.sections: s.key != "design" and s.key != "below"»
* `rptg.talk.context.facts`: «task.report != null => exists s in result.sections: s.key == "report"»
* `rptg.talk.context.facts`: «task.report == null => forall s in result.sections: s.key != "report"»

## Операции, которых пока не вызывает ни одна схема

Их вызовут схемы ещё не разложенных подсистем. I10 (достижимость) проверяется, когда разложено
всё дерево.

—

## Заметки

* утверждение корня от 2026-10-02 действует: хэш карты совпадает
