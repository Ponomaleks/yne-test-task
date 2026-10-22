---
status: Accepted
owner: "Oleksandr Ponomarenko"
reviewers: []
updated_at: "2026-10-22"
feature_size: "S"
ticket: ""
---

# 0004 — Process events in a background task after the acknowledgement and retry by a replay CLI

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Oleksandr Ponomarenko (owner), with the design session

## Context

The architecture map leaves open how the processor is triggered: in the request, in a background
task or by a CLI command. Each event needs several CRM reads (deal, associations, companies, line
items, pipelines), and the CRM allows 20 requests per 10 000 ms (FINDINGS), while a delivery must
be acknowledged within 5 s (spec §6). A retry is a replay of the recorded deliveries (spec §1,
AC-19), and live runs are started only by the human (CLAUDE.md rule 7). This decision also fixes the
feature's target surfaces (sad.md §4).

## Decision drivers

- Delivery acknowledgement ≤ 5 s per delivery, target p95 ≤ 1 s (spec §6).
- 0 duplicate orders or customers across two consecutive full replays; 0 events without a recorded
  outcome per replay (spec §6, AC-12, AC-13, AC-17).
- A retry is a replay of the recorded deliveries; no automatic scheduled retries (spec §3 known
  limitations, AC-19).
- One process, one SQLite file, single writer (ADR-0003); 4-hour time box (ADR-0001).

## Considered options

1. **Background task after the acknowledgement, in the same process; a `replay` CLI as the only
   retry** — the endpoint verifies, persists and acknowledges; FastAPI runs the processing right
   after the response.
2. **Process inside the request before acknowledging** — simplest flow, but one three-event delivery
   needs about 15 paced CRM reads, which does not fit in 5 s.
3. **Separate worker process polling the store** — survives restarts and is closest to production,
   but adds a second process and a polling loop to run, test and explain, and a second process
   writing outcomes while the service writes events would require relaxing ADR-0003's single-writer
   rule.
4. **No processing in the service; a CLI command processes the stored events after a replay** —
   easy to test, but a delivery is never processed without a second operator action, which is not
   how a webhook integration behaves.

## Decision outcome

**Chosen:** Option 1 (owner decision). It meets the acknowledgement target because the handler only
verifies, persists and schedules. It needs no second process. Failed and stranded events are
retried by the same replay that produced them. Rules that come with it:

- The background task processes only the events of its own delivery. An event with no outcome or
  whose last outcome is failed is processed. An event with a final outcome is counted as a
  duplicate event.
- One process-wide lock: only one background task processes at a time, and uvicorn runs one
  worker. Without it, two deliveries of the same deal processed at the same time could both find no
  order and both create one.
- The `replay` CLI fetches the recorded deliveries from the CRM test tool and posts each one byte
  for byte, with its original headers, to the local endpoint, in order. Only the human runs it.
- The signed text uses `HUBSPOT_WEBHOOK_URI`, never the local URL, so replayed deliveries verify.

## Consequences

**Positive**
- The acknowledgement time does not depend on CRM or accounting-system latency.
- One process and one command for the human to run. The retry path is the normal path.
- Processing is a plain function the tests call directly, with faked clients.

**Negative**
- A background task that has not finished when the process stops is lost. Its events stay persisted
  without a final outcome, and the next replay processes them.
- The lock serializes all processing. That is fine for 11 deliveries but would not hold under
  production load.
- The replay CLI cannot print outcomes, because processing finishes after the acknowledgement.
  Outcomes are in the store and in one summary log line per delivery. A separate `report` command
  prints them after the replay (sad.md §8).

**Neutral**
- Moving to Option 3 later reuses the processor unchanged. Only the trigger changes, plus the
  outbox noted in ADR-0003.

## Links

- Spec: [[../spec.md]] §1, §6, AC-12, AC-13, AC-17, AC-19
- SAD: [[../sad.md]] §4, §5, §6
- Related ADR: [[../../../adr/0002-separate-pure-core-from-io-edges]], [[../../../adr/0003-use-sqlite-file-store-with-startup-schema]]
