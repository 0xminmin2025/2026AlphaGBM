"""
API Documentation Module
Serves SKILL.md for AI agents and OpenAPI spec for developers
"""
from flask import Blueprint, send_from_directory, jsonify, Response
import os

docs_bp = Blueprint('docs', __name__, url_prefix='/api/docs')

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

SKILL_MD = """# AlphaGBM — AI Stock & Options Analysis Platform

Base URL: `https://www.alphagbm.com/api`
Auth: `Authorization: Bearer agbm_your_api_key`
Get API Key: https://www.alphagbm.com/api-keys

---

## 1. Quick Queries (instant, no quota cost)

Use these for simple questions like "AAPL股价多少" or "NVDA的IV高不高".

### GET /stock/quick-quote/{ticker}
Stock price, PE, 52-week range. Use for: price check, basic info.
```
GET /api/stock/quick-quote/AAPL
→ {"price": 185.5, "change_pct": 1.2, "pe_ratio": 28.5, "52w_high": 199.6, "sector": "Technology", ...}
```

### GET /options/snapshot/{symbol}
IV Rank, HV, VRP snapshot. Use for: "is IV high/low?", volatility questions.
```
GET /api/options/snapshot/NVDA
→ {"atm_iv": 0.52, "iv_rank": 72.3, "hv_30d": 0.45, "vrp": 0.07, "vrp_level": "moderate_premium"}
```

### GET /options/expirations/{symbol}
List available option expiry dates.
```
GET /api/options/expirations/AAPL
→ {"expirations": ["2026-04-04", "2026-04-11", "2026-04-17", ...]}
```

### GET /options/quote/{symbol}
Real-time stock quote (price, change, volume).
```
GET /api/options/quote/TSLA
→ {"price": 248.5, "change": 3.2, "changePercent": 1.3, "volume": 45123456}
```

### GET /options/recommendations
Today's top-rated option opportunities. Use for: "any good options today?"
```
GET /api/options/recommendations?count=5
→ {"recommendations": [{"symbol": "AAPL", "score": 82, "strategy": "sell_put", ...}]}
```

---

## 2. Full Analysis (10-30s, costs 1 credit)

Use these for deep analysis. Add `?compact=true` to get condensed response (recommended for agents).

### POST /stock/analyze-sync
AI stock analysis with target price, risk score, EV model, and report.
Use for: "分析一下特斯拉", "AAPL worth buying?"
```
POST /api/stock/analyze-sync?compact=true
{"ticker": "TSLA", "style": "balanced"}
→ {"price": 248.5, "target_price": 285, "recommendation": "Buy", "risk_score": 4.2, "ai_summary": "...", ...}
```
Style options: `quality`, `value`, `growth`, `momentum`, `balanced`

### POST /options/chain-sync
Options chain analysis with scoring (0-100) for all strikes. Returns strategy recommendations.
Use for: "分析TSLA的期权", "AAPL 4月期权怎么样?"
```
POST /api/options/chain-sync?compact=true
{"symbol": "TSLA", "expiry_date": "2026-04-17"}
→ {"iv_rank": 65, "overall_recommendation": {...}, "top_calls": [...], "top_puts": [...]}
```

### POST /options/enhanced-sync
Deep analysis of a specific option contract (VRP, Greeks, risk).
Use for: analyzing a particular contract.
```
POST /api/options/enhanced-sync?compact=true
{"symbol": "TSLA", "option_identifier": "TSLA260417C00250000"}
→ {"vrp": {"iv_rank": 65, "vrp_level": "moderate_premium"}, "greeks": {"delta": 0.52, ...}}
```

### POST /options/reverse-score
Score a user-specified option. Use for: "this option good?", "rate my trade".
```
POST /api/options/reverse-score
{"symbol": "AAPL", "option_type": "CALL", "strike": 190, "expiry_date": "2026-04-17", "option_price": 2.50}
→ {"scores": {"sell_call": {"score": 72}, "buy_call": {"score": 65}}, ...}
```

---

## 3. Options Tools (instant, computational)

### POST /options/tools/greeks
Calculate Greeks for any option parameters.
```
POST /api/options/tools/greeks
{"spot": 150, "strike": 155, "expiry_days": 30, "iv": 0.25, "option_type": "call"}
→ {"delta": 0.42, "gamma": 0.03, "theta": -0.08, "vega": 0.18}
```

### POST /options/tools/implied-volatility
Reverse-engineer IV from market price.
```
POST /api/options/tools/implied-volatility
{"spot": 150, "strike": 155, "expiry_days": 30, "market_price": 3.50, "option_type": "call"}
→ {"implied_volatility": 0.283}
```

### GET /options/tools/vol-smile/{symbol}
IV smile curve across strikes for a given expiry.
```
GET /api/options/tools/vol-smile/AAPL?expiry=2026-04-17
→ {"strikes": [...], "call_ivs": [...], "put_ivs": [...], "skew_metrics": {...}}
```

### GET /options/tools/vol-surface/{symbol}
3D volatility surface (strike × expiry × IV).
```
GET /api/options/tools/vol-surface/AAPL?range=all
→ {"surface_data": [...], "term_structure": [...]}
```

### POST /options/tools/strategy/build
Build and analyze multi-leg option strategies.
```
POST /api/options/tools/strategy/build
{"mode": "template", "symbol": "TSLA", "template": "bull_call_spread",
 "params": {"lower_strike": 250, "upper_strike": 260, "expiry": "2026-04-17"}}
→ {"greeks": {...}, "max_profit": 650, "max_loss": -350, "breakeven": 253.5}
```
Templates: bull_call_spread, bear_put_spread, iron_condor, straddle, strangle, covered_call, protective_put, collar

### POST /options/tools/simulate
P/L scenario simulation with bull/base/bear cases.
```
POST /api/options/tools/simulate
{"symbol": "TSLA", "legs": [{"strike": 250, "type": "call", "action": "buy", "expiry": "2026-04-17"}]}
→ {"scenarios": {"bull": {...}, "base": {...}, "bear": {...}}, "probability_of_profit": 0.62}
```

### POST /options/tools/scan
Screen options by strategy, IV, yield. Use for: "find good sell-put candidates".
```
POST /api/options/tools/scan
{"strategies": ["cash_secured_put"], "iv_percentile_min": 60, "min_yield": 1.0}
→ {"results": [{"symbol": "MARA", "score": 85, "annual_yield": 48.2, "iv_rank": 89}, ...]}
```

---

## 4. Account

### GET /user/quota
Check remaining credits.
```
GET /api/user/quota
→ {"total_credits": 47, "daily_free": {"remaining": 2}, "subscription": {"plan_tier": "plus"}}
```

---

## Quota & Rate Limits
- Free: 2 stock + 1 options analysis per day
- Plus: 1,000/month | Pro: 5,000/month
- Rate limit: 60 requests/minute
- Quota exhausted: returns 402 with `{"error": "额度不足", "upgrade_url": "https://www.alphagbm.com/pricing"}`

## Error Codes
| Code | Meaning |
|------|---------|
| 401  | Invalid or missing API Key |
| 400  | Bad request parameters |
| 402  | Quota exhausted |
| 429  | Rate limit exceeded |

## Presentation Guidelines
- Stock: show Rating + Target Price + Risk Score + AI Summary
- Options: show Strategy + Score + Greeks + VRP + Risk warnings
- Always add risk disclaimer: "以上分析仅供参考，不构成投资建议"

## OpenAPI Spec
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
