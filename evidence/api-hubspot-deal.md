# Evidence: HubSpot single deal with associations

- Captured: 2026-10-22, 21:57 (Europe/Oslo)
- Request: `GET {HUBSPOT_BASE_URL}/crm/v3/objects/deals/{dealId}?associations=companies,line_items&properties=amount,dealstage,pipeline,deal_currency_code,closedate,hs_lastmodifieddate,dealname`
- Deal: one `closedwon` deal from the recorded webhooks (technical ID 40211700201)
- Auth: `Authorization: Bearer {HUBSPOT_APP_TOKEN}`
- Result: `HTTP 200`
- Captured by: human, shape only. Numbers and dates are digit-masked (each digit shown as 9). `dealname` type only.

## Response shape

```json
{
  "top_keys": ["id", "properties", "createdAt", "updatedAt", "archived", "associations"],
  "id_type": "string",
  "archived": false,
  "property_types": {
    "amount": "string",
    "closedate": "string",
    "createdate": "string",
    "deal_currency_code": "string",
    "dealname": "string",
    "dealstage": "string",
    "hs_lastmodifieddate": "string",
    "hs_object_id": "string",
    "pipeline": "string"
  }
}
```

## Configuration values and formats

```json
{
  "dealstage": "closedwon",
  "pipeline": "default",
  "deal_currency_code": "NOK",
  "amount_format": "99999",
  "closedate_format": "9999-99-99T99:99:99.999Z",
  "updatedAt_format": "9999-99-99T99:99:99.999Z"
}
```

## Associations

```json
{
  "association_types": ["companies", "line_items"],
  "association_fields": {
    "companies": ["results"],
    "line_items": ["results"]
  },
  "association_counts": {
    "companies": 1,
    "line_items": 1
  },
  "association_has_paging": {
    "companies": false,
    "line_items": false
  },
  "association_result_fields": {
    "companies": { "id": "string", "type": "string" },
    "line_items": { "id": "string", "type": "string" }
  },
  "association_link_types": {
    "companies": ["deal_to_company"],
    "line_items": ["deal_to_line_item"]
  }
}
```

## Notes

- The deal `id` is a string here, while `objectId` in webhook events is a number.
- This deal is a happy path: one company, one line item, NOK, integer amount.
