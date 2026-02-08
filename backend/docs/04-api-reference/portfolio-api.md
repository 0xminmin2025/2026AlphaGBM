# Portfolio API -- 投资组合接口

**Blueprint 前缀**: `/api/portfolio` | **源文件**: `app/api/portfolio.py` | **Auth**: 全部无需认证

---

## 1. POST /api/portfolio/update-holding-dates

一次性操作，将所有持仓的 `created_at` 统一更新为 `2026-01-01`。无需 request body。

**Response:**
```json
{
  "success": true,
  "message": "Successfully updated 20 holdings to 2026-01-01",
  "total_holdings": 20,
  "updated_count": 20
}
```

---

## 2. GET /api/portfolio/holdings

获取按风格分组的持仓，包含实时价格和盈亏。通过 `DataProvider` 获取实时报价，金额通过汇率转 USD。

**Response:**
```json
{
  "success": true,
  "data": {
    "holdings_by_style": {
      "quality": [
        {"ticker": "NVDA", "name": "英伟达", "shares": 214, "cost": 194.2,
         "current": 210.5, "market": "US", "profit_amount": 3488.2,
         "profit_percent": 8.39, "currency": "USD"}
      ],
      "value": [], "growth": [], "momentum": []
    },
    "style_stats": {
      "quality": {
        "profitLossPercent": "12.4", "vsYesterdayPercent": "1.2",
        "market_value": 280000, "investment": 250000
      }
    },
    "chart_data": [
      {"date": "2026-01-15", "quality": 10.4, "value": 5.2, "growth": 8.6, "momentum": 12.8}
    ]
  }
}
```

- **holdings_by_style**: 按 `quality`/`value`/`growth`/`momentum` 分组
- **chart_data**: 最近 30 天 `StyleProfit` 历史，用于前端图表
- 查询失败时返回 fallback 静态数据并附加 `message` 字段

---

## 3. GET /api/portfolio/daily-stats

获取最新一天的投资组合汇总统计。数据来自 `DailyProfitLoss` 表最新记录。

**Response:**
```json
{
  "success": true,
  "data": {
    "total_investment": 1000000,
    "total_market_value": 1150000,
    "total_profit_loss": 150000,
    "total_profit_loss_percent": 15.0,
    "trading_date": "2026-02-07"
  }
}
```

---

## 4. GET /api/portfolio/profit-loss/history

获取每日盈亏历史，含总盈亏与各风格明细。

| Query Param | 类型 | 默认 | 约束 | 说明 |
|-------------|------|------|------|------|
| `days` | int | 30 | max 365 | 查询天数 |

**Response:**
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "date": "2026-01-10",
        "total_investment": 1000000,
        "total_market_value": 1050000,
        "total_profit_loss": 50000,
        "total_profit_loss_percent": 5.0,
        "styles": {
          "quality": {"investment": 250000, "market_value": 275000,
                      "profit_loss": 25000, "profit_loss_percent": 10.0}
        }
      }
    ],
    "period_days": 30,
    "total_records": 22
  }
}
```

数据源：`DailyProfitLoss` + `StyleProfit`。无历史数据时返回模拟渐进增长数据。

---

## 5. GET /api/portfolio/rebalance-history

获取双周再平衡历史记录，按日期降序排列。

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1, "rebalance_date": "2026-01-15", "rebalance_number": 1,
      "holdings_added": 3, "holdings_removed": 1, "holdings_adjusted": 5,
      "total_investment": 1000000, "total_market_value": 1080000,
      "total_profit_loss": 80000, "total_profit_loss_percent": 8.0,
      "style_stats": {}, "changes_detail": {}, "notes": "Bi-weekly rebalance"
    }
  ]
}
```

若 `PortfolioRebalance` 表不存在，返回空数组。

---

## 通用错误响应 (500)

```json
{"success": false, "error": "错误描述"}
```
