# Evidence: HubSpot recorded webhook deliveries

- Captured: 2026-10-22, 21:49 (Europe/Oslo)
- Request: `GET {HUBSPOT_BASE_URL}/_testverktoy/webhooks`
- Auth: `Authorization: Bearer {HUBSPOT_APP_TOKEN}`
- Result: `HTTP 200`
- Captured by: human, shape only. No values, header values or body text.

## Response shape

```json
{
  "top_keys": ["results"],
  "deliveries": 11,
  "paging": "undefined",
  "delivery_fields": {
    "leveranse": "number",
    "method": "string",
    "uri": "string",
    "headers": "object",
    "body": "string"
  },
  "header_names": [
    "Content-Type",
    "X-HubSpot-Signature-v3",
    "X-HubSpot-Request-Timestamp"
  ],
  "uris": ["https://integrasjon.fjordforum.no/webhooks/hubspot"],
  "events_per_delivery": [1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1]
}
```

## Event shape (parsed from `body`)

```json
{
  "event_fields": {
    "eventId": "number",
    "subscriptionId": "number",
    "portalId": "number",
    "appId": "number",
    "occurredAt": "number",
    "subscriptionType": "string",
    "attemptNumber": "number",
    "objectId": "number",
    "propertyName": "string",
    "propertyValue": "string",
    "changeSource": "string",
    "sourceId": "string"
  }
}
```

## Event counts

```json
{
  "subscription_types": {
    "deal.propertyChange": 12,
    "deal.creation": 1
  },
  "changes": {
    "dealstage=closedwon": 8,
    "dealstage=closedlost": 1,
    "dealstage=contractsent": 1,
    "dealstage=84512400": 1,
    "amount": 1
  },
  "distinct_deals": 10,
  "repeated_event_ids": 1,
  "attempt_numbers": [0, 1, 2],
  "distinct_closedwon_deals": 7
}
```
