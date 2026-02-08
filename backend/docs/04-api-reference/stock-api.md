# Stock API -- 股票分析接口

> Blueprint 前缀: `/api/stock`
> 源码文件: `backend/app/api/stock.py`

---

## 端点列表

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/stock/search` | 无 | 模糊搜索股票 |
| POST | `/api/stock/analyze` | `@check_quota` | 股票分析（自动走异步） |
| POST | `/api/stock/analyze-async` | `@require_auth` `@check_quota` | 异步股票分析 |
| GET | `/api/stock/history` | `@require_auth` `@db_retry` | 分析历史列表 |
| GET | `/api/stock/history/{id}` | `@require_auth` `@db_retry` | 分析历史详情 |
| GET | `/api/stock/summary/{ticker}` | `@require_auth` | 股票摘要（期权联动） |

---

## GET /api/stock/search

通过 Yahoo Finance 进行模糊搜索，支持美股、港股、A股多种格式。无需认证，适合 autocomplete 场景。

### 认证

无需认证 (no auth)

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `q` | string | 是 | - | 搜索关键词，支持 ticker / 公司名 |
| `limit` | integer | 否 | `8` | 返回结果数量，最大 `20` |

### 支持的搜索格式

| 市场 | 格式示例 | 说明 |
|------|---------|------|
| 美股 (US) | `AAPL`, `MSFT` | 直接使用 ticker |
| 港股 (HK) | `700`, `0700`, `00700`, `0700.HK` | 自动补零为 4 位 + `.HK` 后缀 |
| A股 (CN) | `600519`, `600519.SS`, `000001.SZ` | 上交所 `.SS`，深交所 `.SZ` |

### 请求示例

```http
GET /api/stock/search?q=AAPL&limit=5 HTTP/1.1
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "results": [
    {
      "ticker": "AAPL",
      "nameCn": "",
      "nameEn": "Apple Inc.",
      "pinyin": "",
      "market": "US"
    }
  ],
  "source": "cache"
}
```

> `source` 字段仅在命中缓存时出现（TTL 缓存，300 秒过期）。

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `ticker` | string | Yahoo Finance 标准 ticker（如 `0700.HK`） |
| `nameCn` | string | 中文名称（当前为空，预留） |
| `nameEn` | string | 英文名称 |
| `pinyin` | string | 拼音（当前为空，预留） |
| `market` | string | 市场代码：`US` / `HK` / `CN` |

### 错误码

| 状态码 | 说明 |
|--------|------|
| `200` | 即使搜索无结果也返回 200，`results` 为空数组 |

### 备注

- 搜索仅返回 `EQUITY`、`ETF`、`FUND`、`MUTUALFUND` 类型
- 内置 TTL 缓存（300 秒，最大 500 条），相同查询不会重复调用 Yahoo Finance
- 会自动尝试多种查询变体以提高匹配率

---

## POST /api/stock/analyze

股票分析主端点。所有完整分析请求均自动走异步任务队列，利用每日缓存避免重复计算。

### 认证

`@check_quota(service_type='stock_analysis', amount=1)` -- 需要认证且消耗 1 credit

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `ticker` | string | 是 | - | 股票代码（自动转大写） |
| `style` | string | 否 | `"quality"` | 分析风格：`quality` / `value` / `growth` / `momentum` |
| `onlyHistoryData` | boolean | 否 | `false` | 仅获取历史数据（用于图表，同步返回） |

### 请求示例

```http
POST /api/stock/analyze HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "ticker": "AAPL",
  "style": "quality"
}
```

### 成功响应 -- 异步任务模式

**Status: `201 Created`**

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Analysis task created successfully"
}
```

### 成功响应 -- onlyHistoryData=true（同步模式）

**Status: `200 OK`**

```json
{
  "success": true,
  "data": {
    "price": 185.50,
    "history": [ ... ]
  }
}
```

### 缓存策略

| 场景 | 行为 |
|------|------|
| Cache HIT | 今日已分析过相同 ticker+style，创建快速任务返回缓存数据 |
| In-progress | 相同 ticker+style 任务正在执行，创建等待任务复用结果 |
| Cache MISS | 创建新的完整分析任务 |

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `No data provided` | 请求体为空 |
| `400` | `Ticker is required` | 未提供 ticker |
| `400` | `找不到股票代码 "XXX" 或数据获取失败` | ticker 无效或数据源无数据 |
| `401` | `Authentication required` | 完整分析需要登录 |
| `402` | `Insufficient Credits` | 额度不足 |
| `500` | `分析过程中发生错误: ...` | 服务器内部错误 |

---

## POST /api/stock/analyze-async

显式异步股票分析端点，行为与 `/analyze` 的异步模式一致，但不支持 `onlyHistoryData` 参数。

### 认证

`@require_auth` + `@check_quota(service_type='stock_analysis', amount=1)`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `ticker` | string | 是 | - | 股票代码（自动转大写） |
| `style` | string | 否 | `"quality"` | 分析风格 |
| `priority` | integer | 否 | `100` | 任务优先级（数值越小优先级越高） |

### 请求示例

```http
POST /api/stock/analyze-async HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "ticker": "TSLA",
  "style": "momentum",
  "priority": 50
}
```

### 成功响应

**Status: `201 Created`**

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Analysis task created successfully"
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `No data provided` | 请求体为空 |
| `400` | `Ticker is required` | 未提供 ticker |
| `401` | `Authentication required` | 未登录 |
| `402` | `Insufficient Credits` | 额度不足 |
| `500` | `Failed to create analysis task: ...` | 任务创建失败 |

---

## GET /api/stock/history

获取当前用户的股票分析历史记录列表，支持分页和 ticker 过滤。

### 认证

`@require_auth` + `@db_retry(max_retries=3, retry_delay=0.5)`

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | `1` | 页码 |
| `per_page` | integer | 否 | `10` | 每页条数，最大 `50` |
| `ticker` | string | 否 | - | 按 ticker 过滤（自动转大写） |

### 请求示例

```http
GET /api/stock/history?page=1&per_page=20&ticker=AAPL HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "success": true,
        "data": { ... },
        "risk": { ... },
        "report": "AI 分析报告文本...",
        "history_metadata": {
          "id": 42,
          "created_at": "2025-01-15T10:30:00",
          "is_from_history": true,
          "ticker": "AAPL",
          "style": "quality"
        }
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 56,
      "pages": 3,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |
| `500` | 数据库查询错误（会自动重试 3 次） |

---

## GET /api/stock/history/{id}

根据历史记录 ID 获取完整的分析详情数据。

### 认证

`@require_auth` + `@db_retry(max_retries=3, retry_delay=0.5)`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 分析历史记录 ID |

### 请求示例

```http
GET /api/stock/history/42 HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

返回完整的分析数据（与分析任务完成时的结果相同），附加 `history_metadata`。

```json
{
  "success": true,
  "data": { ... },
  "risk": { ... },
  "report": "AI 分析报告...",
  "history_metadata": {
    "id": 42,
    "created_at": "2025-01-15T10:30:00",
    "is_from_history": true,
    "ticker": "AAPL",
    "style": "quality"
  }
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `401` | - | 未登录 |
| `404` | `Analysis history not found` | 记录不存在或不属于当前用户 |
| `500` | - | 数据库错误 |

---

## GET /api/stock/summary/{ticker}

获取股票分析摘要，用于期权分析页面与股票分析的联动展示。首次分析免费，历史数据直接返回。

### 认证

`@require_auth`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `ticker` | string | 股票代码（自动转大写） |

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `force_refresh` | string | 否 | `"false"` | 强制重新分析（非首次时消耗 1 credit） |

### 请求示例

```http
GET /api/stock/summary/AAPL?force_refresh=false HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "summary": {
    "ticker": "AAPL",
    "current_price": 185.50,
    "target_price": 195.00,
    "target_price_pct": "+5.1%",
    "stop_loss_price": 175.00,
    "market_sentiment": 7.5,
    "risk_score": 3.2,
    "risk_level": "medium",
    "position_size": 15.0,
    "ev_score": 7.2,
    "recommendation_action": "BUY",
    "ai_summary": "AAPL近期表现强劲...",
    "analyzed_at": "2025-01-15T10:30:00"
  },
  "is_first_time": false,
  "from_history": true,
  "history_id": 42
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `is_first_time` | 是否为该用户对此 ticker 的首次分析 |
| `from_history` | 数据是否来自历史记录（非实时分析） |
| `history_id` | 历史记录 ID（仅 `from_history=true` 时存在） |

### 额度逻辑

| 场景 | 消耗额度 |
|------|---------|
| 首次分析某 ticker | 免费（0 credit） |
| 有历史记录且 `force_refresh=false` | 免费（直接返回历史数据） |
| `force_refresh=true` 且非首次 | 消耗 1 credit |

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `找不到股票代码 "XXX" 或数据获取失败` | ticker 无效 |
| `401` | - | 未登录 |
| `403` | `额度不足，无法重新分析` | 强制刷新时额度不足 |
| `500` | `获取摘要失败: ...` | 服务器内部错误 |
