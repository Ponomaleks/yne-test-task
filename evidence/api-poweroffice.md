# Evidence: PowerOffice token, customer search, order search

- Captured: 2026-10-22, 22:38 (Europe/Oslo)
- Requests (sequential, 600 ms apart):
  - `POST {POWEROFFICE_BASE_URL}/oauth/token` (Basic auth, `grant_type=client_credentials`)
  - per company: `GET {HUBSPOT_BASE_URL}/crm/v3/objects/companies/{id}?properties=orgnr`, then `GET {POWEROFFICE_BASE_URL}/v2/Customers?organizationNumber={normalized orgnr}`
  - `GET {POWEROFFICE_BASE_URL}/v2/SalesOrders?reference=hubspot-deal-40211700201`
- orgnr normalization in the probe: spaces removed, optional `NO` prefix and `MVA` suffix removed, then exactly 9 digits. The orgnr itself is never printed.
- Captured by: human, shape and counts only. The token is never printed.
- Result: all `HTTP 200`, no 429.

## Output (as printed)

```json
{"probe":"token","status":200,"keys":{"access_token":"string","token_type":"string","expires_in":"number"},"token_type":"Bearer","expires_in":900}
{"probe":"customers","company":"21894400101","orgnr_valid":true,"status":200,"top_shape":"array","list_location":"top-level array","matches":0,"match_fields":"undefined"}
{"probe":"customers","company":"21894400102","orgnr_valid":true,"status":200,"top_shape":"array","list_location":"top-level array","matches":1,"match_fields":{"id":"number","name":"string","organizationNumber":"string","emailAddress":"string","countryCode":"string","createdAt":"string"}}
{"probe":"customers","company":"21894400103","orgnr_valid":true,"status":200,"top_shape":"array","list_location":"top-level array","matches":1,"match_fields":{"id":"number","name":"string","organizationNumber":"string","emailAddress":"string","countryCode":"string","createdAt":"string"}}
{"probe":"salesorders","status":200,"top_shape":"array","list_location":"top-level array","matches":0,"match_fields":"undefined","line_fields":null}
```

## Notes

- Search endpoints return a top-level JSON array, not a wrapped object. No paging fields observed.
- Customer `id` is a number; `organizationNumber` is a string.
- Company 21894400101 has no customer yet; 21894400102 and 21894400103 match exactly one existing customer each, found with the normalized 9-digit orgnr.
- No order exists yet for `hubspot-deal-40211700201` (expected before the first live run). Exact versus partial matching of `reference` is not verified yet.
