# rptg kit: reverse PTG on ready tools

[Русская версия](KIT.md)

Started 10.10.2026, for the author's own work and not for sale (decision of 08.10). The kit's own code is only glue:
wherever a ready solution exists, it is used. The first core `rptg/` and its shell `rptg_host/` stay in the
repository as they were.

## What comes from where

| part | the first core had | taken ready-made |
|---|---|---|
| spec from a brief | — | spec template and clarification, at most 5 questions: [GitHub Spec Kit](https://github.com/github/spec-kit) (spec-template, /clarify) |
| requirements and properties | — | EARS "WHEN … THE SYSTEM SHALL …" and "for any …" properties: [AWS Kiro](https://kiro.dev/docs/specs/correctness/) |
| architecture | prompts of its own `talk` | the architect's brief (data, interfaces, call flow): [MetaGPT](https://github.com/FoundationAgents/MetaGPT) |
| decomposition | — | a hierarchy of functions, each with its own tests: [Parsel](https://arxiv.org/abs/2212.10561) |
| executor discipline | — | exactly the task, self-check before submitting, a fresh subagent per task: [superpowers](https://github.com/obra/superpowers) |
| condition language | its own CL compiled to Z3 | conditions in Python: [deal](https://github.com/life4/deal) (`@deal.pre/ensure/has`) |
| types across node links | its own checks | [mypy](https://github.com/python/mypy), strict, over the stubs |
| the import graph, cycles | its own check.graph | [tach](https://github.com/tach-org/tach): ArchUnit-style dependency rules (`tach.toml`, no cycles) |
| banned APIs, printing | its own tree walk | [ruff](https://github.com/astral-sh/ruff): TID251, T20, S |
| side effects | — | `deal lint` (DEL042, DEL046…) |
| conditions at run time, property tests | its own wrappers and generator | deal + [Hypothesis](https://github.com/HypothesisWorks/hypothesis): `deal.cases` |
| symbolic check | — | [CrossHair](https://github.com/pschanely/CrossHair) (`--analysis_kind=deal`) |
| complexity | its own | [radon](https://github.com/rubik/radon); the limit 1.5·D + 5 is our fit over 105 functions (BASIS A11) |
| roles, models, switching | its own loop and API calls | Claude Code subagents: a model per call (sonnet / haiku / opus) |
| "connect from a folder" | — | a Claude Code plugin: MCP server ([FastMCP](https://github.com/modelcontextprotocol/python-sdk)), roles and a skill |
| traversal order | its own plan | `graphlib.TopologicalSorter` from the standard library |

**The kit's own glue:**
- the visibility rule along the card tree;
- examples checked against conditions before any code exists. Nothing ready does this: a stub answers with the
  example's expectation, and deal itself checks the conditions during the doctest;
- task tickets and the model ladder;
- body pasting: an implementer cannot touch the card.

## How it works

- **A card** is a Python module:
  - a node is a module: a leaf is `<name>.py`, a composite is `<name>/__init__.py`;
  - the module docstring says `node: leaf|composite`;
  - every function has a typed signature, `@deal.pre`, `@deal.ensure` and `@deal.has`;
  - the function docstring has `D: <number of decisions>` and doctest examples;
  - the body is `raise NotImplementedError`.

  A module's imports declare what the node may use: types, its children, its siblings and whatever its parent may use.
- **Order:**
  1. The main chat (Opus) is the architect. It writes `spec.md`, then the root, `types.py` and the root's children.
  2. The user approves the root.
  3. A designer (a sonnet subagent) splits each composite node.
  4. An implementer (a haiku subagent) writes a leaf once everything the leaf imports is ready.
  5. A composite node is assembled when its children are ready: its examples and properties run against the real
     children.
- **Checks on every submission** run in a copy of the program, and only accepted work reaches the real one:
  - a decomposition: mypy, tach, ruff, deal lint, visibility, examples against conditions;
  - code: mypy, tach, ruff, deal lint, radon, doctest, deal.cases, CrossHair.

  The tool's report goes to the model as is, and the model repairs its own work: up to 3 submissions per ticket.
- **The ladder:**
  - code: haiku → sonnet → opus;
  - decomposition: sonnet → opus.

  When the ladder is exhausted, the card's owner (the designer of its parent) fixes the card. When the repairs (2) are
  exhausted too, the user is asked (`kit_unblock`). A new version of the root goes back for approval.
- **State** lives in `<project>/.rptg-kit/`:
  - `state.json` and `journal.jsonl`;
  - `trash/`: replaced files go here, nothing is deleted.

  The configuration of the ready checks stays in the program: `pyproject.toml`, `tach.toml`,
  `tests/test_rptg_cases.py`. The boundaries hold after the kit is gone: `python -m pytest`, `python -m tach check`.

## Connecting

The ready checks live in a separate environment `.venv-kit` in the kit folder: `pip install -r requirements-kit.txt`
(deal 4.24.6, crosshair-tool 0.0.111, tach 0.35.3, ruff 0.17.0).

**The environment the program is checked in** (since 11.10.2026):
- If the project folder has a `.venv`, the kit checks with it. Otherwise it uses the kit server's environment.
- The `.venv` is not copied into the program's copy. The copy learns which interpreter to use from the file
  `.rptg-python`.
- Before the checks, the kit makes sure the environment has everything: the packages the program imports and the
  checks themselves.
  - A gap gives an `[env]` report with the install command. The submission does not count, up to twice per ticket.
  - The subagent answers "gave up: environment"; the main chat installs the package and sends the same subagent back.
  - If a package is missing when a composite node is assembled, `kit_next` answers `kind: env`, and the node is not
    sent for repair.
- The packages the program imports are written to the `dependencies` of its `pyproject.toml`.

**Properties under a linked pre-condition.** Example: `0 <= start < end <= len(text)`. Hypothesis tries only inputs
that pass the condition, without the "slow" and "too many filtered" thresholds. If no input passes (Unsatisfiable),
the test is skipped with a reason, and CrossHair checks the properties.

**Functions with side effects** (`@deal.has("io" | "write" | …)`) get no random inputs and no solver: Hypothesis
would feed them random paths. They are checked by their examples, and the examples run in a throwaway copy of the
program.

**Roles** list their allowed tools: the kit's tools (`kit_brief`, `kit_submit`, `kit_guide`, `kit_status`, under both
names, as a plugin and through `.mcp.json`), plus Read, Grep, Glob and ToolSearch. Roles loaded in an open chat are
refreshed only in a new chat.

**As a plugin**, the server and the roles are available in every chat. Once:

```
/plugin marketplace add Deadatreides/REVERSE-PTG
/plugin install rptg@rptg-local
```

A local folder works too: `claude plugin marketplace add <path to REVERSE-PTG>`. Then open a new chat. The roles are
called `rptg:rptg-designer` and `rptg:rptg-implementer` there.

Claude Code keeps a copy of the plugin in `%USERPROFILE%\.claude\plugins\cache\rptg-local\rptg\<version>\`, even
though `plugin list` says "Read from: <folder>". This surfaced on 11.10: the 0.1.0 copy had been taken before an
input fix, and the checks hung under Claude Code.

Since 0.2.0 the server starts through `rptg_kit/launch.py`:
* it takes the kit folder from `~/.rptg-kit/home` if a working checkout is written there, else the plugin's own
  folder;
* it takes Python from `RPTG_KIT_PYTHON`, else that folder's `.venv-kit`, else the Python that runs it.

So:
* **a change to the kit code** in the working checkout applies with a new chat;
* **a change to the roles or the skill** applies with a new version in `plugin.json`, then
  `claude plugin marketplace update rptg-local` and `claude plugin update rptg@rptg-local`.

**For one project folder only**, use `.mcp.json` and `.claude/agents/`:

```bash
<REVERSE-PTG>/.venv-kit/Scripts/python <REVERSE-PTG>/rptg_kit/connect.py <folder>
```

Then open a new chat in that folder; Claude Code asks permission for the rptg server.

**Then tell the next chat:** «develop the program from the spec `<file>` in the folder `<folder>`».

## Rules for Claude: tokens

The main chat is the expensive part. These rules are in the server's instructions, in the `develop` skill and in
[CLAUDE.md](../CLAUDE.md):
1. The higher model is signalled only at the end: the run's result or the silence watcher.
2. After starting the runner and its watcher, end the turn and make no calls until the watcher exits.
3. Without the runner, dispatch whole waves in the background and ignore single-subagent notifications.
4. The architect writes cards only, in a fresh chat with a small context.
5. The kit runs the checks; models run only the final `pytest` after `done`.
6. Workers answer in one line.

## Verified (10.10.2026)

`tests/test_kit.py`, 11 tests, no models: the subagents' answers are recorded, the tools are real.
- **An invoicing program goes the whole way:**
  1. the root;
  2. approval;
  3. decomposition of `billing`;
  4. an implementer's mistake and its repair from the report;
  5. assembly;
  6. the finished program passes `pytest` and `tach check` on its own.
- **Caught:**
  - an example that contradicts its own condition;
  - a designer editing a card;
  - an import of an ancestor;
  - a file outside the node;
  - `os` and `print` in a body;
  - an import that bypasses the graph;
  - a body that lies on one input in billions: only CrossHair found it.
- **The ladder:** haiku → sonnet → opus, then a repair by the owner.
- **Connection:** the server answers over the MCP protocol.

Mutants: 12. Each safeguard was switched off in turn, and its test caught all 12. The plugin passed
`claude plugin validate`; with `--plugin-dir`, Claude Code started the server (`plugin:rptg:rptg … Connected`).

## In use (11.10–17.10.2026)

With live models, the kit built the whole full engine of [PTG-MEM](https://github.com/Deadatreides/PTG-MEM) 0.3:
* memcore: 17 tickets;
* memshell;
* ptgfull: 25 tickets, 2 381 lines, 120 tests;
* ptgcore: 43 tickets, 281 tests, workers $0.69.

Since 13.10 the kit starts its workers itself (`rptg_kit.run`, `claude -p` with the ticket's model and role). The main
chat receives no subagent notifications. Each of them used to be a turn over a large context, about $0.08.

Cost at API prices:
* memcore and memshell: $33.97, against $12.6–14.6 by hand;
* ptgfull: $16.8, against $8–12.

The workers are cheap: Haiku wrote 22 leaves for $0.21–0.25. The main chat is the expensive part. It should write
cards only, without a reference implementation, and work in a fresh chat with a small context.
