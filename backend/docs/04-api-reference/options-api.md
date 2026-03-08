# Options API -- 期权分析接口

> Blueprint 前缀: `/api/options`
> 源码文件: `backend/app/api/options.py`

---

## 端点列表

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/options/chain-async` | `@require_auth` `@check_quota` | 异步期权链分析 |
| POST | `/api/options/enhanced-async` | `@require_auth` `@check_quota` | 异步增强期权分析 |
| GET | `/api/options/expirations/{symbol}` | `@require_auth` | 获取到期日列表 |
| GET/POST | `/api/options/chain/{symbol}/{expiry_date}` | `@check_quota` | 期权链数据（同步/异步） |
| GET | `/api/options/quote/{symbol}` | `@require_auth` | 股票实时报价 |
| GET | `/api/options/history/{symbol}` | `@require_auth` | 股票历史价格 |
| GET/POST | `/api/options/enhanced-analysis/{symbol}/{option_identifier}` | `@check_quota` | 增强分析（VRP/Risk） |
| GET | `/api/options/history` | `@require_auth` `@db_retry` | 分析历史列表 |
| GET | `/api/options/history/{id}` | `@require_auth` `@db_retry` | 分析历史详情 |
| GET | `/api/options/recommendations` | 无 | 每日热门期权推荐 |
| POST | `/api/options/reverse-score` | `@require_auth` `@check_quota` | 反向查分 |
| POST | `/api/options/chain/batch` | `@require_auth` | 批量期权链分析 |
| POST | `/api/options/recognize-image` | `@require_auth` | 期权截图识别 |
| GET | `/api/options/commodity/contracts/{product}` | `@require_auth` | 商品期货合约列表 |

> **白名单校验 (2026-02-09 新增):** `chain-async`, `enhanced-async`, `expirations`, `chain`, `reverse-score` 端点在处理 HK/CN/COMMODITY 市场标的时，会先进行白名单校验。不在白名单内的标的返回 `400` 错误（见下方通用错误码）。

---

## POST /api/options/chain-async

创建异步期权链分析任务。

### 认证

`@require_auth` + `@check_quota(service_type='option_analysis', amount=1)`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `symbol` | string | 是 | - | 股票代码 |
| `expiry_date` | string | 是 | - | 到期日，格式 `YYYY-MM-DD` |
| `priority` | integer | 否 | `100` | 任务优先级（越小越高） |

### 请求示例

```http
POST /api/options/chain-async HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "symbol": "AAPL",
  "expiry_date": "2025-03-21",
  "priority": 100
}
```

### 成功响应

**Status: `201 Created`**

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Options analysis task created successfully"
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `Request body is required` | 请求体为空 |
| `400` | `symbol and expiry_date are required` | 缺少必填参数 |
| `401` | `Authentication required` | 未登录 |
| `402` | `Insufficient Credits` | 额度不足 |
| `500` | `Failed to create options analysis task: ...` | 任务创建失败 |

---

## POST /api/options/enhanced-async

创建异步增强期权分析任务（含 VRP 分析、风险评估等）。

### 认证

`@require_auth` + `@check_quota(service_type='option_analysis', amount=1)`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `symbol` | string | 是 | - | 股票代码 |
| `option_identifier` | string | 是 | - | 期权合约标识符（如 `AAPL250321C00190000`） |
| `expiry_date` | string | 否 | - | 到期日，用于历史记录 metadata |
| `priority` | integer | 否 | `100` | 任务优先级 |

### 请求示例

```http
POST /api/options/enhanced-async HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "symbol": "AAPL",
  "option_identifier": "AAPL250321C00190000",
  "expiry_date": "2025-03-21"
}
```

### 成功响应

**Status: `201 Created`**

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Enhanced options analysis task created successfully"
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `Request body is required` | 请求体为空 |
| `400` | `symbol and option_identifier are required` | 缺少必填参数 |
| `401` | `Authentication required` | 未登录 |
| `402` | `Insufficient Credits` | 额度不足 |
| `500` | `Failed to create enhanced options analysis task: ...` | 任务创建失败 |

---

## GET /api/options/expirations/{symbol}

获取指定股票的可用期权到期日列表。

### 认证

`@require_auth`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |

### 请求示例

```http
GET /api/options/expirations/AAPL HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

返回 `ExpirationResponse` Pydantic 模型序列化结果，包含可选到期日期列表。

```json
{
  "symbol": "AAPL",
  "expirations": ["2025-02-21", "2025-03-21", "2025-04-17", "2025-06-20"]
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |
| `500` | 数据获取失败 |

---

## GET/POST /api/options/chain/{symbol}/{expiry_date}

获取指定到期日的期权链数据和评分。支持同步 (GET) 和异步 (POST) 两种模式。

### 认证

`@check_quota(service_type='option_analysis', amount=1)`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |
| `expiry_date` | string | 到期日，格式 `YYYY-MM-DD` |

### POST Request Body (JSON) -- 异步模式

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `async` | boolean | 否 | `false` | 设为 `true` 启用异步模式 |
| `priority` | integer | 否 | `100` | 异步任务优先级 |

### 请求示例 -- 同步模式

```http
GET /api/options/chain/AAPL/2025-03-21 HTTP/1.1
Authorization: Bearer <token>
```

### 请求示例 -- 异步模式

```http
POST /api/options/chain/AAPL/2025-03-21 HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "async": true,
  "priority": 50
}
```

### 成功响应 -- 同步模式

**Status: `200 OK`**

返回 `OptionChainResponse` Pydantic 模型序列化结果。

### 成功响应 -- 异步模式

**Status: `201 Created`**

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Options analysis task created successfully"
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 异步模式需要登录 |
| `402` | 额度不足 |
| `500` | 数据获取或分析失败 |

---

## GET /api/options/quote/{symbol}

获取股票实时报价信息（用于期权分析页面展示标的信息）。

### 认证

`@require_auth`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |

### 成功响应

**Status: `200 OK`**

返回 `StockQuoteResponse` Pydantic 模型序列化结果。

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |
| `500` | 报价获取失败 |

---

## GET /api/options/history/{symbol}

获取指定股票的历史价格数据（用于期权分析中的价格走势图）。

### 认证

`@require_auth`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `days` | integer | 否 | `60` | 历史天数 |

### 请求示例

```http
GET /api/options/history/AAPL?days=90 HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "dates": ["2025-01-02", "2025-01-03", ...],
  "prices": [185.50, 186.20, ...]
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |
| `500` | 数据获取失败 |

---

## GET/POST /api/options/enhanced-analysis/{symbol}/{option_identifier}

获取指定期权合约的增强分析，包含 VRP (Variance Risk Premium) 分析和风险评估。

### 认证

`@check_quota(service_type='option_analysis', amount=1)`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |
| `option_identifier` | string | 期权合约标识符（如 `AAPL250321C00190000`） |

### POST Request Body (JSON) -- 异步模式

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `async` | boolean | 否 | `false` | 设为 `true` 启用异步模式 |
| `priority` | integer | 否 | `100` | 异步任务优先级 |
| `expiry_date` | string | 否 | - | 到期日，用于历史记录 metadata |

### 成功响应 -- 同步模式

**Status: `200 OK`**

返回 `EnhancedAnalysisResponse` Pydantic 模型序列化结果。

### 成功响应 -- 异步模式

**Status: `201 Created`**

```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "Enhanced options analysis task created successfully"
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 异步模式需要登录 |
| `402` | 额度不足 |
| `500` | 分析失败 |

---

## GET /api/options/history

获取当前用户的期权分析历史记录列表。

### 认证

`@require_auth` + `@db_retry(max_retries=3, retry_delay=0.5)`

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | `1` | 页码 |
| `per_page` | integer | 否 | `10` | 每页条数，最大 `50` |
| `symbol` | string | 否 | - | 按 symbol 过滤（自动转大写） |

### 请求示例

```http
GET /api/options/history?page=1&per_page=20&symbol=AAPL HTTP/1.1
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
        "vrp_analysis": { ... },
        "risk_analysis": { ... },
        "history_metadata": {
          "id": 15,
          "created_at": "2025-01-15T10:30:00",
          "is_from_history": true,
          "symbol": "AAPL",
          "option_identifier": "AAPL250321C00190000",
          "expiry_date": "2025-03-21",
          "analysis_type": "enhanced"
        }
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 30,
      "pages": 2,
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
| `500` | 数据库查询错误 |

---

## GET /api/options/history/{id}

根据历史记录 ID 获取完整的期权分析详情。

### 认证

`@require_auth` + `@db_retry(max_retries=3, retry_delay=0.5)`

### Path Parameters

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 分析历史记录 ID |

### 成功响应

**Status: `200 OK`**

返回完整分析数据，附加 `history_metadata`。

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `401` | - | 未登录 |
| `404` | `Options analysis history not found` | 记录不存在或不属于当前用户 |
| `500` | - | 数据库错误 |

---

## GET /api/options/recommendations

获取每日热门期权推荐，无需登录。

### 认证

无需认证 (no auth)

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `count` | integer | 否 | `5` | 返回推荐数量，范围 `1-10` |
| `refresh` | string | 否 | `"false"` | 是否强制刷新缓存 |

### 请求示例

```http
GET /api/options/recommendations?count=5 HTTP/1.1
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "recommendations": [
    {
      "symbol": "AAPL",
      "option_type": "CALL",
      "strike": 190,
      "expiry_date": "2025-03-21",
      "score": 85
    }
  ],
  "market_summary": { ... },
  "updated_at": "2025-01-21T09:30:00Z"
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `500` | 推荐服务不可用 |

---

## POST /api/options/reverse-score

反向查分：根据用户手动输入的期权参数计算评分，无需从期权链中选择。

### 认证

`@require_auth` + `@check_quota(service_type='option_analysis', amount=1)`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `symbol` | string | 是 | - | 股票代码 |
| `option_type` | string | 是 | - | 期权类型：`CALL` 或 `PUT` |
| `strike` | number | 是 | - | 行权价（必须 > 0） |
| `expiry_date` | string | 是 | - | 到期日，格式 `YYYY-MM-DD` |
| `option_price` | number | 是 | - | 期权价格（必须 > 0） |
| `implied_volatility` | number | 否 | 自动估算 | 隐含波动率（小数或百分比均可，如 `0.28` 或 `28`） |

### 请求示例

```http
POST /api/options/reverse-score HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "symbol": "AAPL",
  "option_type": "CALL",
  "strike": 190,
  "expiry_date": "2025-03-21",
  "option_price": 2.50,
  "implied_volatility": 28
}
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "symbol": "AAPL",
  "option_type": "CALL",
  "strike": 190,
  "expiry_date": "2025-03-21",
  "days_to_expiry": 25,
  "option_price": 2.50,
  "implied_volatility": 28.0,
  "stock_data": { ... },
  "scores": {
    "sell_call": { "score": 72, "style_label": "稳健收益" },
    "buy_call": { "score": 65, "style_label": "激进策略" }
  },
  "trend_info": { ... }
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `{field} is required` | 缺少必填参数 |
| `400` | `option_type must be CALL or PUT` | 期权类型无效 |
| `400` | `strike must be positive` | 行权价无效 |
| `400` | `option_price must be positive` | 期权价格无效 |
| `400` | `expiry_date must be in YYYY-MM-DD format` | 日期格式错误 |
| `401` | - | 未登录 |
| `402` | - | 额度不足 |
| `500` | `反向查分失败: ...` | 服务器内部错误 |

### 备注

- `implied_volatility` 如果传入值大于 1（如 `28`），系统自动除以 100 转为小数（`0.28`）
- 如果不提供 `implied_volatility`，系统将根据历史数据自动估算

---

## POST /api/options/chain/batch

批量创建期权链分析任务，支持多个 symbol 和多个 expiry_date 的笛卡尔积组合。

### 认证

`@require_auth`（额度在函数内部手动检查和扣减）

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `symbols` | string[] | 是 | - | 股票代码数组，最多 `3` 个 |
| `expiries` | string[] | 是 | - | 到期日数组，最多 `2` 个，格式 `YYYY-MM-DD` |
| `priority` | integer | 否 | `100` | 任务优先级 |

### 额度消耗

消耗 credits = `len(symbols)` x `len(expiries)`

例如：2 个 symbol + 2 个 expiry = 4 credits

### 请求示例

```http
POST /api/options/chain/batch HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "symbols": ["AAPL", "TSLA"],
  "expiries": ["2025-02-21", "2025-03-21"],
  "priority": 100
}
```

### 成功响应

**Status: `201 Created`**

```json
{
  "success": true,
  "task_ids": [
    { "symbol": "AAPL", "expiry": "2025-02-21", "task_id": "uuid-1" },
    { "symbol": "AAPL", "expiry": "2025-03-21", "task_id": "uuid-2" },
    { "symbol": "TSLA", "expiry": "2025-02-21", "task_id": "uuid-3" },
    { "symbol": "TSLA", "expiry": "2025-03-21", "task_id": "uuid-4" }
  ],
  "total_queries": 4,
  "quota_info": {
    "is_free": false,
    "free_remaining": 0,
    "free_quota": 2
  }
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `symbols array is required` | symbols 缺失或非数组 |
| `400` | `expiries array is required` | expiries 缺失或非数组 |
| `400` | `Maximum 3 symbols allowed` | 超过 symbol 数量上限 |
| `400` | `Maximum 2 expiry dates allowed` | 超过 expiry 数量上限 |
| `401` | `Authentication required` | 未登录 |
| `402` | 额度不足信息 | 附带 `remaining_credits`、`free_remaining`、`code: "INSUFFICIENT_CREDITS"` |
| `500` | `Failed to create batch tasks: ...` | 任务创建失败 |

---

## POST /api/options/recognize-image

上传期权截图，通过 AI 图像识别自动提取期权参数（symbol、strike、expiry 等）。

### 认证

`@require_auth`

### Request

- **Content-Type**: `multipart/form-data`
- **字段**: `image` -- 图片文件

### 文件限制

| 限制项 | 值 |
|--------|-----|
| 最大文件大小 | 10 MB |
| 支持格式 | `PNG`、`JPG`、`JPEG`、`WebP` |

### 请求示例

```http
POST /api/options/recognize-image HTTP/1.1
Authorization: Bearer <token>
Content-Type: multipart/form-data; boundary=----FormBoundary

------FormBoundary
Content-Disposition: form-data; name="image"; filename="option_screenshot.png"
Content-Type: image/png

<binary data>
------FormBoundary--
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "option_type": "CALL",
    "strike": 230,
    "expiry_date": "2025-02-21",
    "option_price": 5.50,
    "implied_volatility": 0.28,
    "confidence": "high",
    "notes": "从 Robinhood 截图中识别"
  }
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `请上传图片文件` | 请求中没有 `image` 字段 |
| `400` | `未选择文件` | 文件名为空 |
| `400` | `不支持的文件格式。支持: png, jpg, jpeg, webp` | 文件扩展名不在允许列表 |
| `400` | `文件大小不能超过 10MB` | 文件超过大小限制 |
| `401` | - | 未登录 |
| `500` | `图片识别失败: ...` | AI 识别服务异常 |

---

## GET /api/options/commodity/contracts/{product}

> **2026-02-09 新增**

查询商品期货期权的可用合约列表及主力合约。

### 认证

`@require_auth`

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `product` | string | 商品品种代码: `au`(黄金), `ag`(白银), `cu`(沪铜), `al`(沪铝), `m`(豆粕) |

### 请求示例

```http
GET /api/options/commodity/contracts/au HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "success": true,
  "product": "au",
  "product_name": "黄金",
  "exchange": "SHFE",
  "contracts": ["au2604", "au2605", "au2606", "au2608", "au2610", "au2612"],
  "dominant_contract": "au2604",
  "multiplier": 1000
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `product` | string | 品种代码 |
| `product_name` | string | 品种中文名 |
| `exchange` | string | 交易所代码 (SHFE/DCE) |
| `contracts` | string[] | 可用合约列表（按持仓量排序） |
| `dominant_contract` | string | 主力合约（持仓量最大） |
| `multiplier` | integer | 合约乘数 |

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `不支持的商品品种: {product}` | 品种不在支持列表中，响应含 `supported` 字段列出所有支持品种 |
| `401` | - | 未登录 |
| `500` | `获取合约数据失败` | AkShare 数据源异常 |

---

## 通用错误：白名单校验失败

> **2026-02-09 新增**，适用于 `chain-async`, `enhanced-async`, `expirations`, `chain`, `reverse-score` 端点

当请求的标的不在对应市场的白名单中时：

**Status: `400 Bad Request`**

```json
{
  "success": false,
  "error": "标的 9618.HK 不在 HK 市场期权白名单中",
  "allowed_symbols": ["0700.HK", "9988.HK", "3690.HK"]
}
```

白名单规则：US 市场无白名单限制；HK、CN、COMMODITY 市场强制白名单（详见期权分析模块 Section 1.1）。

---

## GET /api/options/recommendations — 响应字段补充

> **2026-02-09 更新**

每个推荐项新增以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `market` | string | 标的所属市场: `US` / `HK` / `CN` / `COMMODITY` |
| `currency` | string | 计价币种: `USD` / `HKD` / `CNY` |
