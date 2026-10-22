# CLAUDE.md

Project rules for Claude Code. Read this fully before acting.

## Context

- This is a time-boxed (4 hours) integration assignment between two TEST systems of a fictional customer. Nothing real is affected.
- The task has been received. The stack is chosen in sdd survey. Do not invent requirements.
- The method is Spec-Driven Development with the `sdd` plugin (`/sdd:*` commands). Follow its flow. Do not create parallel planning or decision documents outside sdd. Agent execution through sdd (implement, team mode, worktree isolation) is allowed. The local decision log in .claude/*.local.md is a git-ignored record for the human and is not an sdd artifact. Exception: docs/FINDINGS.md is a running log of behavior that differs from the API documentation or from expectations. Add an entry as soon as a difference is found: date, system, what the docs say, what was observed, and how it was handled. No personal values. It is used for the delivery explanation.
- Stack, project structure, and tooling are decided in the sdd foundation step (`survey`, `scaffold`) and recorded as ADRs (`design`, `decide-adr`).
- Nobody on the assignment provider's side can be asked. Decide, record the decision in the relevant sdd document, and move on.
- `evidence/` holds raw API output pasted by the human: HTTP status, top-level keys, counts, pagination fields and types only. No values, tokens or personal data. It is read-only input for sdd. Never write, reformat or delete files there.

## Language (strict)

Everything is in English: chat replies, questions to the human (AskUserQuestion labels and descriptions), documents, code, comments, tests, commit messages, and PR text. This overrides any plugin guidance that asks for another language. Do not translate identifiers.

## Working rules

1. One vertical slice at a time: the smallest end-to-end behavior that works against a test system, with tests. A slice is one milestone of tasks in `tasks.json`. Tasks inside the current milestone may run in parallel (sdd team or workflow mode); the next milestone starts only after the current one is green and committed.
2. Tests ship with the code. A bug fix starts with a failing test.
3. Keep diffs small. If a step is large, split it and say why.
4. Before saying "done": run the project's check command (defined during scaffold) and report its result. Never claim tests pass without running them.
5. Do not invent API behavior. If an endpoint, field, auth flow, limit, or error format is unknown, say so and ask the human for the docs or a sample response. Verified facts (from `evidence/` or docs the human provided) are recorded only in the sdd document of the current stage: `docs/idea-brief.md` during interview, `spec.md` during specify, `sad.md` during design. Later stages cite that document instead of restating the fact.
6. Ask the human before: adding a dependency, changing the project structure, changing CI or config, or deleting files. Calls to external systems are covered by rule 7. Exception: the CI, config and structure that `survey` planned are created by `scaffold` without asking again; later changes to them need approval.
7. Calls to external systems: the agent never runs the application against a real or test external system, even with the human's approval, and never builds requests with credentials itself. It may prepare the exact command and explain what it will do. The human runs it and pastes back a summary of the result.
8. Keep it readable. The author must be able to explain and change any line live in an interview. No clever abstractions, no dead code.

## Engineering principles

Stack and layout still come from sdd survey; survey treats these as inputs.

- Scope: no features, layers or abstractions "for later".
- Structure: one responsibility per module. Core logic is pure, without I/O; I/O happens only at
  the edges. The concrete modules are decided in sdd design.
- Abstractions only at external system boundaries (HTTP clients), so tests can use fakes.
  No DI frameworks, generic repositories or plugin systems.
- Naming: domain terms from the API docs (canonical list in CONTEXT.md). Comments explain why.
- Errors: never swallow an error. Failures that block all work (config, auth, unreachable system)
  stop with a clear message. A failure in one unit of work is logged with its ID, counted, and the
  other units of work continue. A failed unit of work stays persisted and can be retried. It is
  never only logged. Before any create in an external system, look up by an external key.
  Retry a write only after that lookup.
- Tests: the check command is hermetic: no containers or browsers. No outbound network. Endpoint
  tests call the app in-process or on localhost. Mock HTTP at the client
  boundary with synthetic fixtures shaped like `evidence/`. Most tests target mapping and validation.
  Runs against a test system are manual, per rule 7.
- Live run: any command that calls an external system is not a test and is run only by the human,
  manually. Never create a script or target named `test:integration`, `test:e2e` or `integration` in any
  build file. All automated tests are hermetic and run through the standard test command.
- Test integrity: never change or remove a test to make it pass. If a test seems wrong, explain and wait.
- Gates: standard defaults. Nothing stricter than common practice.

## Security and customer data

- Secrets live only in `.env` (git-ignored). Never read, print, echo, log, or commit them. Commit `.env.example` with placeholder values only.
- If a command is blocked by the security hook, stop and ask the human. Do not rephrase, split or re-quote the command to get around the block.
- Load configuration in one place, validate it at startup, and fail with the names of missing variables, never their values.
- Treat all data from external systems as customer data that may contain personal data. Do not paste real records into chat, documents, commits, or test fixtures. Fixtures are synthetic.
- Application output (logs, console, reports) must not contain personal values from the external systems. Log counts, statuses, technical IDs, durations and error types instead.
- Never disable TLS verification. Never commit tokens, cookies, or full request dumps.
- Only call the hosts of the two test systems. No other outbound calls.

## Integration checklist (apply per slice)

Implement what the slice needs. Record the rest as known limitations in the sdd docs.

- Auth: acquisition, refresh, expiry, 401 handling.
- Pagination: never assume a single page.
- Errors: a timeout on every request. Retry only transient failures (network errors, 429, 5xx), honoring Retry-After. Do not blindly retry non-idempotent writes.
- Idempotency: re-running must not create duplicates (external IDs, or look up before create).
- Validation: validate inbound payloads at the boundary. A bad record is reported, not fatal.
- Partial failure: one bad unit of work does not block the others; failed units of work stay persisted for retry. Summarize successes and failures.
- Observability: structured logs with the delivery or event ID, counts, and durations.
- Dry run for anything that writes to a target system.
- Locale specifics when relevant: date and time zones, decimal and currency units, character encoding.

## Git

- sdd commits each document and each task. This is allowed.
- Commit messages: Conventional Commits for manual commits. Commits made by sdd keep sdd's own format (`<stage>: <slug> <doc>`, `<type>(<slug>): <title>` with `SDD-Task`/`SDD-AC` trailers).
- Never force-push, never rewrite history, never commit `.env*` except `.env.example`.
- Branch: before the first sdd stage, create `feat/<slug>`. sdd document stages commit to the current branch.
- The human pushes. The agent never pushes; when a milestone is green and committed, it says so and prints the push command for the human to run.

## Communication

- Be concise. Lead with what changed and what the human needs to do.
- When unsure, give two options with trade-offs and a recommendation. If the decision is reversible, proceed and record the assumption. If it is not reversible, wait for the human.

## Commands

Foundation: [docs/architecture-map.md](docs/architecture-map.md).

- Venv: `python -m venv .venv`, then activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` elsewhere).
- Install: `python -m pip install -e .[dev]`
- Check (rule 4): `ruff check . && pytest`
- Run: `python -m app`
