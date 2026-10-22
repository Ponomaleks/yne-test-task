# AI workflow
 
How I used AI on this assignment, how I steered it, and where I had to step in.
 
## Tools
 
- **Claude Code** with the **sdd** plugin (spec-driven development). Every stage writes a document
  to the repo and commits it: brief, spec, architecture map and ADRs, scaffold, design (SAD),
  sequences, data model, API contract, tasks, implementation.
- **A second Claude chat** as a reviewer and prompt writer. I gave it my decisions in Ukrainian; it
  reviewed each stage's output against the task, the evidence and the time box, and wrote the
  English prompts I sent to Claude Code.
## Guardrails set before the task
 
- **`CLAUDE.md`**: working rules, engineering principles, security rules, git workflow. The key
  rules: the agent never calls the test systems (I ran every probe and live run myself); secrets
  only in `.env`, never read or printed; hermetic tests; no blind retry of writes; ask before
  deleting files; never weaken a test to make it pass.
- **Secrets hook**: blocks commands that could read `.env`. When it blocked the agent, the agent
  stopped and asked instead of rewording the command, as `CLAUDE.md` requires.
- **sdd settings**: `require_integration: never`, so the implementation gate never runs anything
  that could reach a live system.
- **Branch protection**: main accepts changes only through pull requests.
- **Decision log**: a hook records every multiple-choice answer I gave the agent
  (`.claude/decisions-log.local.md`, git-ignored).
## How I steered
 
1. **Evidence before the spec.** The agent planned to write the spec from the docs. I moved the API
   probes first. I ran each probe myself and pasted back only shapes, types and counts into
   `evidence/`. The probes found most of the traps: a won stage in a second pipeline, a deal whose
   last event says won while the deal is not, a German company with a "DE" orgnr prefix, a deal in
   EUR, string metadata, and the real rate limit.
2. **Owner decisions passed as text.** For each stage I answered the agent's questions with explicit
   decisions (scope, hold rules, processing trigger, replay as retry), so it did not invent them.
3. **Scope cut early.** I fixed a slice-1 scope and a list of known limitations in the spec, and told
   the critic to classify findings as "must fix" or "known limitation" without adding criteria.
4. **Time box.** Each late stage got a time limit and "easy" depth. The report command was planned
   as the last, droppable task and was dropped.
## Where I stepped in
 
| What the agent proposed or did                              | What I changed                                                                    | Why                                                                        |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Deduplicate by event ID once an event was "processed"       | Only a final outcome counts; a failed event is processed again                    | Otherwise a failed event would never be retried: an order could be lost    |
| HTTP clients retry on 5xx and timeouts for every call       | Retry only GET and 429; never retry a POST, look up by external key first         | A retried POST after a timeout can create a duplicate order                |
| One SQLite connection per process                           | A short-lived connection per operation                                            | FastAPI runs sync handlers and background tasks in other threads           |
| `requires-python >= 3.14`                                   | `>= 3.12`, developed on 3.14                                                      | A reviewer with an older Python could not install it                       |
| Normalize orgnr by keeping digits                           | Accept only an optional "NO" prefix and "MVA" suffix; any other prefix is foreign | "DE 123 456 789" would become a valid Norwegian number: the wrong customer |
| Rename environment variables, spread rules into `CLAUDE.md` | Keep project decisions in sdd documents; `CLAUDE.md` keeps stable rules only      | One source of truth per decision                                           |
| Report "one line per deal"                                  | One line per event                                                                | A deal with two events would hide that its order was created               |
 
## What the manual run caught
 
The unit tests were green (157 tests), but my manual run found:
 
- A response model typed a numeric field (`leveranse`) as text, against the captured evidence. The
  synthetic test fixture had the same mistake, so the tests passed. Lesson: fixtures must be checked
  against the evidence, not only shaped like it.
- The store folder was not created on a clean checkout.
- The app does not load `.env` itself, and INFO logging was not configured.
- One recorded delivery is forged: its signature does not match. The signature check rejected it,
  as designed (see `docs/FINDINGS.md`).
- In the live run PowerOffice rejected the creates. The failures were recorded and kept for a
  replay, but the cause was not found within the time box, because the app logs only the error type.
## What I would do differently
 
- Run a dry run against the test systems as soon as the first end-to-end path exists, not after all
  tasks are done.
- Log external error codes and field names (never values) from the start, so a live failure can be
  diagnosed without a code change.
 