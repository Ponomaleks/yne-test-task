# Evidence: HubSpot summary, follow-up

- Captured: 2026-10-22, 22:01 (Europe/Oslo)
- Scope: deals 40211700204, 40211700206, 40211700209, and the company and line item of 40211700205
- Requests: same as `api-hubspot-deals-summary.md`, spaced by the rate limit headers of the first response
- Captured by: human, technical IDs, codes and digit masks only (each digit shown as 9)
- Result: completed, no 429. One `404` for deal 40211700209.

## Output (as printed)

```json
{"ratelimit_max":"20","ratelimit_interval_ms":"10000","spacing_ms":600}
{"deal":"40211700204","events":["dealstage=closedwon"],"dealstage":"closedwon","pipeline":"default","deal_currency_code":"NOK","amount_mask":"9999","companies_count":1,"line_items_count":1,"companies":[{"id":"21894400104","orgnr_mask":null,"country":"Norway","fakturaepost_null":false}],"lines":[{"id":"52300900304","property_types":{"amount":"string","createdate":"string","discount":"null","hs_lastmodifieddate":"string","hs_object_id":"string","name":"string","price":"string","quantity":"string"},"price_mask":"9999","quantity_mask":"9","discount_mask":null}]}
{"deal":"40211700206","events":["dealstage=closedwon","amount"],"dealstage":"closedwon","pipeline":"default","deal_currency_code":"NOK","amount_mask":"99999","companies_count":1,"line_items_count":2,"companies":[{"id":"21894400101","orgnr_mask":"999999999","country":"Norway","fakturaepost_null":false}],"lines":[{"id":"52300900306","property_types":{"amount":"string","createdate":"string","discount":"null","hs_lastmodifieddate":"string","hs_object_id":"string","name":"string","price":"string","quantity":"string"},"price_mask":"99999","quantity_mask":"9","discount_mask":null},{"id":"52300900307","property_types":{"amount":"string","createdate":"string","discount":"null","hs_lastmodifieddate":"string","hs_object_id":"string","name":"string","price":"string","quantity":"string"},"price_mask":"9999","quantity_mask":"9","discount_mask":null}]}
{"error_status":404,"at":"deal 40211700209"}
{"deal":"40211700205","events":["dealstage=84512400"],"dealstage":"84512400","pipeline":"84512397","deal_currency_code":"EUR","amount_mask":"99999","companies_count":1,"line_items_count":1,"companies":[{"id":"21894400105","orgnr_mask":"DE 999 999 999","country":"Germany","fakturaepost_null":false}],"lines":[{"id":"52300900305","property_types":{"amount":"string","createdate":"string","discount":"null","hs_lastmodifieddate":"string","hs_object_id":"string","name":"string","price":"string","quantity":"string"},"price_mask":"99999","quantity_mask":"9","discount_mask":null}]}
```

## Notes

- Rate limit headers: 20 requests per 10 000 ms.
- `Retry-After` was not observed (no 429 in this run).
- Deal 40211700209 has a recorded `closedwon` event but returns `404` from the deals API.
