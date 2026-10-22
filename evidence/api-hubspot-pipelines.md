# Evidence: HubSpot deal pipelines

- Captured: 2026-10-22, 21:52 (Europe/Oslo)
- Request: `GET {HUBSPOT_BASE_URL}/crm/v3/pipelines/deals`
- Auth: `Authorization: Bearer {HUBSPOT_APP_TOKEN}`
- Result: `HTTP 200`
- Captured by: human, shape and pipeline configuration only. Labels not captured.

## Response shape

```json
{
  "top_keys": ["results"],
  "pipelines": 2,
  "paging": "undefined",
  "pipeline_fields": {
    "id": "string",
    "label": "string",
    "displayOrder": "number",
    "stages": "array"
  },
  "stage_fields": {
    "id": "string",
    "label": "string",
    "displayOrder": "number",
    "metadata": "object"
  },
  "metadata_fields": {
    "isClosed": "string",
    "probability": "string"
  },
  "stages_per_pipeline": {
    "84512397": 4,
    "default": 5
  }
}
```

## Stages

All `isClosed` and `probability` values are strings.

| pipeline_id | stage_id | isClosed | probability |
|---|---|---|---|
| default | appointmentscheduled | "false" | "0.2" |
| default | qualifiedtobuy | "false" | "0.4" |
| default | contractsent | "false" | "0.9" |
| default | closedwon | "true" | "1.0" |
| default | closedlost | "true" | "0.0" |
| 84512397 | 84512398 | "false" | "0.3" |
| 84512397 | 84512399 | "false" | "0.7" |
| 84512397 | 84512400 | "true" | "1.0" |
| 84512397 | 84512401 | "true" | "0.0" |

`stage_84512400_found`: true
