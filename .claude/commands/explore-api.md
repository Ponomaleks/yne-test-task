---
description: Verify the real shape of an external API before designing against it
argument-hint: <system name> <endpoint or goal>
---

Goal: check the real response shape of an external API before we design against it: $ARGUMENTS

Rules:
- Do NOT read `.env` or any secret file. Refer to secrets by variable name only, as listed in `.env.example`.
- Do NOT run any request yourself. Do NOT create or edit any file.
- Give the human ONE copy-paste read-only `curl` command. Credentials come only from environment
  variables (`$VAR`), never inline values. Print the status and only the shape with `jq`, never the body.
- Accept back from the human only: HTTP status, top-level keys, item count, pagination fields,
  and field types of one item. Refuse personal values, tokens, or headers.
- Tell the human to save the accepted shape as `evidence/api-<name>.md`.
- Facts go only into the sdd document of the current stage: `docs/idea-brief.md` during interview,
  `spec.md` during specify, `sad.md` during design (see CLAUDE.md rule 5).
- If a variable is missing from `.env.example`, tell the human to add it. Do not edit the file yourself.