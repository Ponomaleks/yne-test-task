# Findings

Running log of behavior that differs from the API documentation or from expectations.
One entry per difference: date, system, what the docs say, what was observed, how it was handled.
No personal values.

## 2026-10-22 - HubSpot - Won stage is not always `closedwon`

- Docs say: the deal example and the webhook example use `dealstage` = `closedwon`. Pipelines return
  stages with `metadata.isClosed` and `metadata.probability`.
- Observed: a recorded webhook moves a deal to stage `84512400`. That stage is in a second pipeline,
  `84512397`, with `isClosed` "true" and `probability` "1.0", so it is a won stage. Evidence:
  `evidence/api-hubspot-webhooks.md`, `evidence/api-hubspot-pipelines.md`.
- Handled: a deal is won when its stage has `isClosed` "true" and probability 1.0 in any pipeline,
  resolved through the pipelines API, not by hardcoded stage IDs. Recorded as a rule for the spec.

## 2026-10-22 - HubSpot - Pipeline stage metadata values are strings

- Docs say: all values in `properties` are text, even numbers. Nothing is said about the types of
  pipeline stage `metadata`.
- Observed: `metadata.isClosed` and `metadata.probability` are strings in every stage of both
  pipelines (for example "true", "1.0"). Evidence: `evidence/api-hubspot-pipelines.md`.
- Handled: the won check parses them: `isClosed` must equal "true", and `probability` must parse to
  the number 1.0. Recorded as a rule for the spec.

## 2026-10-22 - HubSpot - Rate limit is 20 requests per 10 000 ms

- Docs say: HubSpot limits calls per ten seconds, returns the limit in `X-HubSpot-RateLimit-Max`,
  `X-HubSpot-RateLimit-Remaining` and `X-HubSpot-RateLimit-Interval-Milliseconds`, and answers
  `429 Too Many Requests` when it is exceeded. No number is given.
- Observed: the headers state 20 requests per 10 000 ms. Our first summary probe used 300 ms
  spacing (about 33 requests per 10 s), exceeded the limit and got `429` after about 17 requests.
  With spacing derived from the headers (600 ms), the follow-up probe completed without `429`.
  `Retry-After` was not observed. Evidence: `evidence/api-hubspot-deals-summary.md`,
  `evidence/api-hubspot-deals-summary-2.md`.
- Handled: 429 handling is required: respect the rate-limit headers and retry after the interval.
  Recorded as a rule for the spec.

## 2026-10-22 - HubSpot - Deal in a recorded webhook returns 404

- Docs say: `GET /crm/v3/objects/deals/{id}` returns one deal. Nothing is said about recorded
  webhook events for deals that no longer exist.
- Observed: deal 40211700209 has a recorded `closedwon` event, but the deals API returns `404` for
  it. Evidence: `evidence/api-hubspot-deals-summary-2.md`.
- Handled: such a deal is held with the reason "deal not found" and is not retried automatically.
  Recorded as a rule for the spec.
