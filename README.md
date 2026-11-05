# REVERSE-PTG (rptg kit)

[Русская версия](README.ru.md)

**A spec becomes a graph of typed cards. Cheap models write the leaves. Ready tools, not models, accept the work.**

A Claude Code plugin for writing a Python program from a spec:

1. **The main chat (Opus) is the architect.** It writes `spec.md`, the root card, the shared types and the root's
   children.
2. **You approve the root.**
3. **Designers (Sonnet subagents)** split each composite node into child cards.
4. **Implementers (Haiku subagents)** write the body of each leaf, strictly to its card.

A card is an ordinary Python module:
* signatures with types;
* [deal](https://github.com/life4/deal) conditions (`@deal.pre`, `@deal.ensure`, `@deal.has`);
* the number of decisions `D` and doctest examples;
* a body of `raise NotImplementedError`.

Nobody can change a card from below. The kit pastes the implementer's body into the card itself.

Every submission is checked in a copy of the program, and only accepted work reaches the real one:

| what is checked | by |
|---|---|
| types across node boundaries | mypy, strict |
| who may import whom; no cycles | [tach](https://github.com/tach-org/tach): ArchUnit-style rules for Python |
| banned APIs, prints, unsafe calls | ruff (TID251, T20, S) |
| side effects match the declared ones | `deal lint` |
| examples and properties | doctest and `deal.cases` ([Hypothesis](https://github.com/HypothesisWorks/hypothesis)) |
| bodies that lie on rare inputs | [CrossHair](https://github.com/pschanely/CrossHair), symbolic |
| size of each function | [radon](https://github.com/rubik/radon), at most 1.5·D + 5 decisions (fitted on 105 functions) |

The tool's report goes back to the model as is, and the model repairs its own work, up to 3 submissions per ticket.
If a submission keeps failing, the ticket climbs a ladder:
* code: haiku → sonnet → opus;
* decomposition: sonnet → opus.

After the ladder, the card's owner fixes the card. After that, you decide (`kit_unblock`).

## What is borrowed from whom

The kit is mostly glue around ready tools and published methods:

| part | taken from |
|---|---|
| spec template, at most 5 clarifying questions | [GitHub Spec Kit](https://github.com/github/spec-kit) |
| EARS requirements, "for any …" properties | [AWS Kiro](https://kiro.dev/docs/specs/correctness/) |
| architect's brief: data, interfaces, call flow | [MetaGPT](https://github.com/FoundationAgents/MetaGPT) |
| a hierarchy of functions, each with its tests | [Parsel](https://arxiv.org/abs/2212.10561) |
| executor discipline: exactly the task, self-check, a fresh subagent per task | [superpowers](https://github.com/obra/superpowers) |
| traversal order | `graphlib.TopologicalSorter` |

Four things are the kit's own:
* **Visibility along the card tree.** A node may use its types, its children, its siblings and what its parent may
  use.
* **Examples are checked against conditions before any code exists.** A stub answers with the example's expectation,
  and deal checks the conditions during the doctest.
* **Tickets and the model ladder.**
* **Body pasting.** An implementer cannot touch the card.

## Install

You need Claude Code, Python 3.11+ on `PATH` as `python`, and a logged-in console `claude` if you want the kit to
start its workers itself.

```bash
git clone https://github.com/Deadatreides/REVERSE-PTG.git
cd REVERSE-PTG
python -m venv .venv-kit
.venv-kit/Scripts/python -m pip install -r requirements-kit.txt   # Linux/macOS: .venv-kit/bin/python
```

Then, in Claude Code:

```
/plugin marketplace add Deadatreides/REVERSE-PTG
/plugin install rptg@rptg-local
```

Or in one step on Claude Code 2.1.275 or later:

```
/plugin install rptg --marketplace Deadatreides/REVERSE-PTG
```

The plugin starts its server through `rptg_kit/launch.py`. The launcher picks the Python like this:
1. `RPTG_KIT_PYTHON` if set;
2. else the `.venv-kit` next to the plugin;
3. else the Python that runs it.

Claude Code runs a cached copy of the plugin. To work on the kit itself, put the path of your checkout into
`~/.rptg-kit/home`, and the launcher will serve from there.

## Use

Open a new chat and say: «develop the program from the spec `<file>` in the folder `<folder>`». You can also run the
skill `rptg:develop`.

The main chat writes the spec and the root, then asks you to approve the root. After that, the kit runs the workers
itself in waves, outside the session. It writes one line per wave to `.rptg-kit/run-progress.log`:

```bash
.venv-kit/Scripts/python -m rptg_kit.run <project folder> --detach
```

Without a logged-in console `claude`, the main chat dispatches the subagents itself (`kit_next`, then one subagent per
ticket).

When the run reaches `done`, the program passes `python -m pytest` and `python -m tach check` on its own, and its
boundaries stay in its `tach.toml`.

## What it has built

The kit was made for the author's own work, and this is what it built:

* **[PTG-MEM](https://github.com/Deadatreides/PTG-MEM) 0.3: the whole full engine, four packages.**
  * `memcore`: 17 tickets.
  * `memshell`.
  * `ptgfull`: 25 tickets, 2 381 lines, 120 tests.
  * `ptgcore`: 43 tickets, 281 tests. Its workers cost $0.69.
* **A graph language model engine** for the author's research (`graphlm`): every check green.

## What it costs (measured, API prices)

| project | through the kit | estimate by hand | |
|---|---|---|---|
| memcore + memshell | $33.97 | $12.6–14.6 | the main chat also fixed the kit and wrote a reference the workers then rewrote |
| ptgfull, 2 381 lines | $16.8 | $8–12 | $6.58 of it is the main chat reacting to worker notifications |

Workers are cheap: Haiku wrote 22 leaves for $0.21–0.25. The expensive part is the main chat. Every notification
from a subagent is a turn over a large context, about $0.08 each.

The kit now starts its workers itself (`rptg_kit.run`), so the main chat receives no notifications. Two more rules
keep the cost down:
* the architect writes cards only, never a full reference implementation;
* the architect works in a fresh chat with a small context.

The full token rules for Claude, with the main one ("the higher model is signalled only at the end"), are in
[CLAUDE.md](CLAUDE.md). The server, the skill and the roles carry them too.

Without these rules, a single strong chat writing the code is cheaper. With them, what you pay for is the contract:
every leaf meets its card, and the boundaries hold after the kit is gone.

## Two generations

* **`rptg/` and `rptg_host/`: the first core**, 27.09–08.10.2026.
  * It had its own condition language compiled to Z3, its own checks, planner, model router, builder and benchmark,
    and a window.
  * It was built by its own method, with 3 287 tests.
  * It never ran live on models.
  * On 08.10 a market check showed that its core idea was already covered: Kiro, Spec Kit, MetaGPT, Parsel, and
    Aider's architect/editor mode with auto-tests.
* **`rptg_kit/`: the kit**, from 10.10.2026. It keeps the cards and the graph and replaces everything else with the
  ready tools above. The old core stays in the repository as it was, with its documents in `docs/` and `design/`.

## Documentation

| document | what it covers | languages |
|---|---|---|
| [docs/KIT.en.md](docs/KIT.en.md) | the kit in full: what comes from where, how cards and checks work, connecting, what was verified, what it built and cost | [English](docs/KIT.en.md), [Russian](docs/KIT.md) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | the first core: decisions, modules, data, pipeline, models and roles, checks, window, safety | Russian |
| [docs/LOGIC.md](docs/LOGIC.md) | the first core's logic: entities, flow model, invariants, the condition language, routing, escalation, acceptance | Russian |
| [docs/BASIS.md](docs/BASIS.md) | the measured facts behind each decision and the assumptions still to measure | Russian |
| [design/](design/) | the first core described by its own method: the map, 215 types, 207 operations, 479 examples | Russian |

## Tests

```bash
.venv-kit/Scripts/python -m pytest tests -q
```

* `tests/test_kit.py` drives a whole program from root to `done` with recorded subagent answers and real tools.
  Twelve mutants, one per disabled safeguard, are all caught.
* The rest are the first core's tests.

## Status

Built for one person's work: Windows 10, Claude Code with Opus, Sonnet and Haiku. It works daily, but it has not
been tried on other machines. Issues are read, but there is no support obligation.

## License

AGPL-3.0-or-later.
