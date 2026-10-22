# Tracker — won-deal-to-order

> Status of every task in the epic. `implement` updates **Status** and **Step** after every
> subagent it runs (and commits them with the task), so this table shows where the run is right now.
> Status: `todo` · `in_progress` · `blocked` · `review` · `done`.
> Step: `SELECT` · `RED` · `GREEN` · `REFACTOR` · `GATE` · `REVIEW` · `COMMIT` (`—` before the task starts).
> A `blocked` row carries its reason in Step, e.g. `GATE — lint red after 3 retries`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status | Step |
|---|---|---|---|---|---|---|---|
| T1 | Promote the four staged tables into app/schema.sql | migration | Oleksandr Ponomarenko | S | — | todo | — |
| T2 | Add store functions for deliveries, events, outcomes and rejections | infra | Oleksandr Ponomarenko | S | T1 | todo | — |
| T3 | Verify the HubSpot v3 signature in a pure function | domain | Oleksandr Ponomarenko | S | — | done | COMMIT |
| T4 | Normalize the orgnr and detect foreign registrations | domain | Oleksandr Ponomarenko | S | — | todo | — |
| T5 | Resolve won stages from the pipeline configuration | domain | Oleksandr Ponomarenko | S | — | todo | — |
| T6 | Map a deal and its line items to a Draft order with percentage discounts | domain | Oleksandr Ponomarenko | S | — | done | COMMIT |
| T7 | Decide skip and hold outcomes as pure rules | domain | Oleksandr Ponomarenko | M | T4, T5 | todo | — |
| T8 | Build the HubSpot client with pacing, 429 wait and GET retries | infra | Oleksandr Ponomarenko | M | — | todo | — |
| T9 | Build the PowerOffice client with token, lookups and creates | infra | Oleksandr Ponomarenko | M | — | todo | — |
| T10 | Process one event from the current deal state to one outcome | app | Oleksandr Ponomarenko | M | T2, T6, T7, T8, T9 | todo | — |
| T11 | Process a delivery's events under one lock, counting duplicates and failures | app | Oleksandr Ponomarenko | S | T10 | todo | — |
| T12 | Add the webhook endpoint: verify, persist, acknowledge, schedule | ports | Oleksandr Ponomarenko | M | T2, T3 | todo | — |
| T13 | Replay recorded deliveries byte for byte to the local endpoint | ports | Oleksandr Ponomarenko | S | T8 | todo | — |
| T14 | Print the run report from the store | ports | Oleksandr Ponomarenko | S | T2 | todo | — |
| T15 | Load config once and wire serve, replay and report commands | wiring | Oleksandr Ponomarenko | S | T11, T12, T13, T14 | todo | — |

**Total:** 15 tasks (10 S, 5 M), ~4 person-days at S = 1–2 h, M = 3–4 h.
