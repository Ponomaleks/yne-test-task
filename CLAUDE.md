# CLAUDE.md

Project rules for Claude Code. Read this fully before acting.

## Context

- This is a time-boxed (4 hours) integration assignment between two TEST systems of a fictional customer. Nothing real is affected.
- The task description arrives at the start of the assignment. Until then, do NOT choose a stack, create application code, or invent requirements.
- The method is Spec-Driven Development with the `sdd` plugin (`/sdd:*` commands). Follow its flow. Do not create parallel planning or decision documents outside sdd. Agent execution through sdd (implement, team mode, worktree isolation) is allowed. The local decision log in .claude/*.local.md is a git-ignored record for the human and is not an sdd artifact.
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
6. Ask the human before: adding a dependency, changing the project structure, changing CI or config, deleting files, or running anything that calls a test system. Exception: the CI, config and structure that `survey` planned are created by `scaffold` without asking again; later changes to them need approval.
7. Calls to the test systems: the agent never builds requests with credentials itself. With the human's approval it may run the project's own app or test command against a test system; the app loads `.env` by itself, and the agent never prints, logs or inspects the values. Report only status codes, counts and record IDs from such a run.
8. Keep it readable. The author must be able to explain and change any line live in an interview. No clever abstractions, no dead code.

## Security and customer data

- Secrets live only in `.env` (git-ignored). Never read, print, echo, log, or commit them. Commit `.env.example` with placeholder values only.
- If a command is blocked by the security hook, stop and ask the human. Do not rephrase, split or re-quote the command to get around the block.
- Load configuration in one place, validate it at startup, and fail with the names of missing variables, never their values.
- Treat all data from external systems as customer data that may contain personal data. Do not paste real records into chat, documents, commits, or test fixtures. Fixtures are synthetic.
- Logs contain IDs, counts, and durations. No personal fields.
- Never disable TLS verification. Never commit tokens, cookies, or full request dumps.
- Only call the hosts of the two test systems. No other outbound calls.

## Integration checklist (apply per slice)

Implement what the slice needs. Record the rest as known limitations in the sdd docs.

- Auth: acquisition, refresh, expiry, 401 handling.
- Pagination: never assume a single page.
- Errors: a timeout on every request. Retry only transient failures (network errors, 429, 5xx), honoring Retry-After. Do not blindly retry non-idempotent writes.
- Idempotency: re-running must not create duplicates (external IDs, or look up before create).
- Validation: validate inbound payloads at the boundary. A bad record is reported, not fatal.
- Partial failure: one bad record does not abort the run. Summarize successes and failures.
- Observability: structured logs with a run ID, counts, and durations.
- Dry run for anything that writes to a target system.
- Locale specifics when relevant: date and time zones, decimal and currency units, character encoding.

## Git

- sdd commits each document and each task. This is allowed.
- Conventional commit messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Never force-push, never rewrite history, never commit `.env*` except `.env.example`.
- The human pushes. The agent never pushes; when a milestone is green and committed, it says so and prints the push command for the human to run.

## Communication

- Be concise. Lead with what changed and what the human needs to do.
- When unsure, give two options with trade-offs and a recommendation. If the decision is reversible, proceed and record the assumption. If it is not reversible, wait for the human.
