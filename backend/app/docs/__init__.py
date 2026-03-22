"""
API Documentation Module
Serves SKILL.md for AI agents and OpenAPI spec for developers
"""
from flask import Blueprint, send_from_directory, jsonify, Response
import os

docs_bp = Blueprint('docs', __name__, url_prefix='/api/docs')

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

SKILL_MD = """# AlphaGBM API — AI-Powered Stock & Options Analysis

## Overview
AlphaGBM provides stock and options analysis via REST API.
API users authenticate with an API Key (prefix `agbm_`), which shares quota with the web account.

Base URL: `https://www.alphagbm.com/api`

## Authentication
All endpoints require an `Authorization` header:
```
Authorization: Bearer agbm_your_api_key
```
Get your API Key at: https://www.alphagbm.com/api-keys

## Endpoints

### 1. Stock Analysis (Async)
Analyze a stock with AI-generated report, risk scoring, target price, and EV model.

```
POST /api/stock/analyze-async
Content-Type: application/json

{"ticker": "TSLA", "style": "balanced"}
```

**Style options:** `quality`, `value`, `growth`, `momentum`, `balanced`

**Response (202):**
```json
{"task_id": "uuid-here", "status": "pending"}
```

### 2. Options Chain Analysis (Async)
Analyze an options chain with scoring for a given expiry date.

```
POST /api/options/chain-async
Content-Type: application/json

{"symbol": "TSLA", "expiry_date": "2026-04-17"}
```

**Response (202):**
```json
{"task_id": "uuid-here", "status": "pending"}
```

### 3. Enhanced Options Analysis (Async)
Deep analysis of a specific option contract (Greeks, VRP, risk assessment).

```
POST /api/options/enhanced-async
Content-Type: application/json

{"symbol": "TSLA", "option_identifier": "TSLA260417C00250000"}
```

**Response (202):**
```json
{"task_id": "uuid-here", "status": "pending"}
```

### 4. Poll Task Result
All analysis endpoints are async. Poll this endpoint every 2-3 seconds until `status` is `completed` or `failed`.

```
GET /api/tasks/{task_id}
```

**Status flow:** `pending` → `processing` → `completed` | `failed`

**Response when completed (200):**
```json
{
  "id": "uuid",
  "status": "completed",
  "progress_percent": 100,
  "result_data": { ... full analysis result ... },
  "completed_at": "2026-03-22T12:00:00"
}
```

### 5. Check Quota
Check remaining analysis credits for the authenticated user.

```
GET /api/user/quota
```

**Response (200):**
```json
{
  "total_credits": 47,
  "daily_free": {"quota": 3, "used": 1, "remaining": 2},
  "subscription": {"plan_tier": "plus", "has_subscription": true}
}
```

### 6. Get Option Expiry Dates
List available expiry dates for a symbol.

```
GET /api/options/expirations/{symbol}
```

### 7. API Key Management
```
GET    /api/keys              — List your API keys
POST   /api/keys              — Create a new key (body: {"name": "My Key"})
DELETE /api/keys/{id}         — Delete a key
POST   /api/keys/{id}/toggle  — Enable/disable a key
```

## Quota & Rate Limits
- API calls consume the same credits as the website
- Free: 2 stock + 1 options analysis per day
- Plus: 1,000 queries/month
- Pro: 5,000 queries/month
- Rate limit: 60 requests/minute (API Key users only)
- When quota is exhausted, API returns:
```json
{"error": "额度不足", "upgrade_url": "https://www.alphagbm.com/pricing"}
```

## Error Codes
| Code | Meaning |
|------|---------|
| 401  | Invalid or missing API Key |
| 400  | Bad request parameters |
| 429  | Rate limit exceeded (retry after 60s) |
| 402  | Quota exhausted — upgrade at /pricing |
| 500  | Server error |

## Output Format Guidelines
When presenting results to the user:
- **Stock analysis:** Rating (Buy/Hold/Sell) + Target Price + Risk Score (0-10) + AI Summary
- **Options analysis:** Recommended strategy + Score + Greeks + VRP analysis + Risk warnings
- Always include the risk disclaimer when showing analysis results

## OpenAPI Spec
Machine-readable spec available at:
- YAML: https://www.alphagbm.com/api/docs/openapi.yaml
- JSON: https://www.alphagbm.com/api/docs/openapi.json
"""


@docs_bp.route('/')
def docs_index():
    """Serve SKILL.md as plain text for AI agents"""
    return Response(SKILL_MD, mimetype='text/plain; charset=utf-8')


@docs_bp.route('/openapi.yaml')
def openapi_spec():
    """Serve the OpenAPI YAML specification"""
    return send_from_directory(DOCS_DIR, 'openapi.yaml', mimetype='text/yaml')


@docs_bp.route('/openapi.json')
def openapi_json():
    """Serve the OpenAPI specification as JSON"""
    import yaml
    yaml_path = os.path.join(DOCS_DIR, 'openapi.yaml')

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        return jsonify(spec)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
