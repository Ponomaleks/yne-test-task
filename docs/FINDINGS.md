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

## 2026-10-23 - HubSpot test tool - One recorded delivery has an invalid signature

- Docs say: every recorded delivery is signed with the app's client secret, exactly as sent.
- Observed in the manual run: 10 of 11 recorded deliveries verify. Delivery 10 does not: its
  signature does not match. It carries a won event (event 1010) for deal 40211700209, which returns
  404 from the deals API. It behaves like a forged delivery.
- Handled: the endpoint rejects it with 401 `delivery.signature_mismatch` before anything is stored
  or processed (AC-15). The rejection keeps only the timestamp header and a SHA-256 of the body.
  The spec's AC-17 and §7 are corrected: deal 40211700209 is no longer expected to be held for
  "deal not found".

## 2026-10-23 - PowerOffice - Order line price field is `unitPriceExVat`

- Docs say: a sales order line has `description`, `quantity`, `unitPrice` and `discountPercent`.
- Observed in the live run: every `POST /v2/SalesOrders` failed with
  `400 ValidationError fields=Lines[0].UnitPriceExVat`. The test system requires the line price in
  `unitPriceExVat`. Found through the error logging (status, error code and field names only).
  The first live run created the customer for company 21894400101 before its order failed; the next
  run found that customer by orgnr and reused it, so no duplicate customer was created.
- Handled: order lines send the price as `unitPriceExVat`; all other fields are unchanged.

## 2026-10-23 - PowerOffice - Order created although the create returned 502

- Docs say: nothing about a 5xx response to `POST /v2/SalesOrders`, or whether the order may still
  exist after one. Our own rule (sad.md, AC-13) assumes it can: a POST is never retried by the
  client, and a retry first looks up the order by the deal's external key.
- Observed in the live run: `POST /v2/SalesOrders` for deal 40211700202 returned `502`, but the
  order was created (order 9002). Verified by the owner with a read-only search by reference
  `hubspot-deal-40211700202`; the order's `createdAt` matches the time of the `502`.
- Handled: by the existing rule, no code change. The client did not retry the POST, and the event
  was recorded as failed. The next replay found the order by its external key and recorded
  "order already exists" instead of creating a duplicate (AC-13).

## 2026-10-23 - HubSpot - Line item discount is returned only when requested

- Docs say: HubSpot lists `discount` as a line item property outside the defaults, which is
  returned only when it is named in `properties`. The client fetched line items without
  `properties`.
- Observed: after the live run, a check of the orders in PowerOffice showed order 9003 (deal
  40211700203) with `discountPercent` 0, although its line item has a discount. The line has price
  28000, quantity 3 and a discount of 4000 per unit, so the expected line total is 72000; the order
  was created with 84000. Cause confirmed by the owner with a read-only check: `GET
  /crm/v3/objects/line_items/52300900303` without `properties` returns no `discount` field; with
  `properties=name,price,quantity,discount` it returns `discount` "4000". The client used the
  first form, so the discount was read as missing and sent as 0.
- Evidence note: the evidence probes requested `discount` explicitly, so they could not show this.
  The request line in the header of `evidence/api-hubspot-deals-summary.md` omits `properties`, but
  every line there has a `discount` key (`null` where there is no discount), which a default
  response leaves out. That header line was incomplete and is corrected in a31bc62.
- Handled: line items are requested with `properties=name,price,quantity,discount`. A new guard
  holds a deal with the reason "order total does not match deal amount" unless the sum over its
  line items of quantity x (price - discount per unit) equals the deal amount (for this line
  3 x (28000 - 4000) = 72000). It runs before any
  customer lookup or create, so a held deal leaves nothing in PowerOffice. Order 9003 itself is not
  corrected by the integration.

## 2026-10-23 - PowerOffice - A non-NOK order currency is accepted and kept

- Docs say: nothing on whether a sales order may use a currency other than NOK; the evidence probes
  did not cover it. The integration sends the deal currency as `currencyCode` and never assumes
  one (sad.md, internationalisation).
- Observed: a manual check by the owner in Postman. A sales order with `currencyCode` "EUR" on an
  existing customer was accepted as Draft, and the response kept `currencyCode` "EUR" and
  `totalExVat` 1000 unchanged (order 9005, reference "manual-test-eur-1", created by hand, not by
  the integration).
- Handled: no code change. The integration passes the deal currency and the test system stores it,
  so a non-NOK currency is not a hold reason. Exchange rates and VAT for foreign customers stay a
  production question for finance.

## 2026-10-23 - PowerOffice - A foreign customer can be created, but duplicates are not prevented

- Docs say: the task API docs describe the customer search by name as matching customers whose
  name contains the text. For the search by `organizationNumber` they say only that it returns
  customers with this organization number. Exact versus partial matching is not verified; we only
  know that the normalized 9-digit orgnr found the expected customers (evidence/api-poweroffice.md).
- Observed: a manual check by the owner in Postman. `POST /v2/Customers` with `countryCode` "DE"
  and no `organizationNumber` was accepted (customer 6002). The same request sent again created
  customer 6003, identical to 6002. PowerOffice does not prevent duplicate customers without an
  orgnr.
- Handled: no code change. For task question 3: a foreign customer can be created technically, but
  without a reliable key the integration cannot find it again safely. A name search that matches on
  "contains" is no safe lookup, and there is no orgnr to look up by. Holding foreign customers stays
  the right default until a stable key is agreed, for example the HubSpot company ID stored on the
  customer, or a VAT number. The manual test records (customers 6002 and 6003, order 9005) stay in
  the test system.
