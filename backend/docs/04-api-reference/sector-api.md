# Sector API -- 板块分析接口

**Blueprint 前缀**: `/api/sector` | **源文件**: `app/api/sector.py`

三大功能模块：板块轮动分析、资金结构分析、缓存管理。除 cache/clear 外均无需认证。

---

## 一、板块轮动分析 (Sector Rotation)

### 1. GET /api/sector/rotation/overview

获取板块轮动概览，包含所有板块强度排名。

| Query Param | 类型 | 默认 | 说明 |
|-------------|------|------|------|
| `market` | string | `US` | 市场代码：`US`/`HK`/`CN`（非法值修正为 US） |

**Response:** `{"success": true, "sectors": [...], "market": "US", ...}`

---

### 2. GET /api/sector/rotation/sector/{name}

获取单板块详情。Path param `name` 为板块名称（如 `Technology`）。

| Query Param | 类型 | 默认 | 说明 |
|-------------|------|------|------|
| `market` | string | `US` | 市场代码 |

**Response (200):** `{"success": true, "data": {"sector_name": "...", "strength": 85.2, ...}}`

**Response (404):** `{"success": false, "error": "Sector not found"}`

---

### 3. GET /api/sector/stock/{ticker}/sector-analysis

分析个股板块关联度和同步性。`ticker` 自动转大写。

| Query Param | 类型 | 默认 | 说明 |
|-------------|------|------|------|
| `sector` | string | `Technology` | 所属板块 |
| `industry` | string | -- | 所属行业（可选） |
| `market` | string | `US` | 市场代码 |

**Response:** `{"success": true, "data": {"ticker": "AAPL", "sync_score": 0.87, ...}}`

---

### 4. GET /api/sector/heatmap

获取板块热力图数据。

| Query Param | 类型 | 默认 |
|-------------|------|------|
| `market` | string | `US` |

**Response:** `{"success": true, "data": [{"sector": "Technology", "value": 2.5, ...}]}`

---

### 5. GET /api/sector/top-sectors

获取强势板块排行。

| Query Param | 类型 | 默认 | 约束 |
|-------------|------|------|------|
| `market` | string | `US` | -- |
| `limit` | int | `5` | 1-20 |

**Response:** `{"success": true, "data": [{"sector": "Technology", "score": 92.5}]}`

---

### 6. GET /api/sector/bottom-sectors

获取弱势板块排行。参数和响应格式与 `/top-sectors` 相同。

---

### 7. GET /api/sector/available-sectors

获取指定市场所有可用板块列表。

| Query Param | 类型 | 默认 |
|-------------|------|------|
| `market` | string | `US` |

**Response:** `{"success": true, "data": ["Technology", "Healthcare", ...]}`

---

## 二、资金结构分析 (Capital Structure)

所有 Path param `ticker` 自动转大写。

### 8. GET /api/sector/capital/analysis/{ticker}

分析个股完整资金结构（资金流向、集中度、结构特征）。

**Response:** `{"success": true, "data": {"ticker": "AAPL", "capital_flow": {...}, ...}}`

---

### 9. GET /api/sector/capital/factor/{ticker}

快速获取资金因子数值（轻量接口）。

**Response:** `{"success": true, "ticker": "AAPL", "capital_factor": 0.75}`

---

### 10. GET /api/sector/capital/stage/{ticker}

获取个股当前情绪传导阶段。

**Response:** `{"success": true, "ticker": "AAPL", "data": {"stage": "accumulation", ...}}`

---

### 11. GET /api/sector/capital/stages

获取所有情绪传导阶段定义。无参数。

**Response:** `{"success": true, "data": [{"stage": "accumulation", "description": "..."}]}`

---

### 12. GET /api/sector/capital/signals/{ticker}

获取资金集中度信号列表。

**Response:**
```json
{
  "success": true,
  "ticker": "AAPL",
  "signals": [{"signal_type": "concentration_spike", "strength": "strong", ...}]
}
```

---

## 三、缓存管理

### 13. POST /api/sector/cache/clear

清除板块轮动和资金结构缓存。**需要认证** (`@require_auth`)。

**Request Body (可选):**

| 字段 | 类型 | 说明 |
|------|------|------|
| `market` | string | 清除指定市场的板块轮动缓存 |
| `ticker` | string | 清除指定股票的资金结构缓存 |

不传参数时清除全部缓存。

**Response:** `{"success": true, "message": "缓存已清除"}`

---

## 通用错误响应 (500)

```json
{"success": false, "error": "错误描述"}
```
