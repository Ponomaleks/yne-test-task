# How I worked with AI

<!-- AGENT INSTRUCTIONS (delete this whole comment block when the file is filled):
Fill this file only when the human asks for it, at the end of the work, not during it.
Use only facts from: git history (git log), docs/ (sdd artifacts and ADRs),
.claude/decisions-log.local.md if it exists, and test results the human pasted in chat.
Do not invent entries. If a section has no source data, write "No data recorded."
Keep every heading exactly as written. Do not rename, add or reorder sections.
Use plain hyphens, not dash characters. -->

## Tool and model
- Tool: Claude Code with the `sdd` plugin (fork: <owner>/sdd, commit <sha>).
- Model: <copy what `/status` shows in the session>.
- Work period: <first and last commit timestamps from git log>.

## Guardrails (as configured, with known limits)
- CLAUDE.md: <one line per rule group: working rules, security and customer data, git rules>.
- .claude/settings.json: <one line each: allow, ask, deny, defaultMode>.
- PreToolUse hook `protect-secrets.mjs`: a text filter on tool input. Blocks direct reads of
  `.env` and key files, and recursive searches that do not exclude `.env`.
- Permission deny rules: <list the Read and Edit rules for secret paths>.
- Sandbox: not used. The Claude Code docs say the Bash sandbox runs on macOS, Linux and WSL2 only.
- Secrets: entered by the human into `.env`, which is git-ignored. Test fixtures are synthetic.

## Workflow (sdd)
- Stages run, per feature: <list from docs/features/<slug>/ and the commit messages>.
- Handoff blocks and /clear: <as actually used, not as planned>.

## Interventions (human decisions)
Source: .claude/decisions-log.local.md and the ADR files in docs/adr/.
One line per intervention, in order:
`<time> <stage> -> AI proposed <X>; I decided <Y>, because <Z>.`
A change that has no log entry is not listed here.

## Tests and checks I ran myself
- <test>: <result as the human reported it in chat>.

## Known limitations
- The PreToolUse hook is a text filter, not a sandbox. Glob patterns such as `.en?` and shell
  loops over dotfiles are not blocked.
- <add only limits that were actually observed during the work>.