# Sector Rotation 模块

## 1. 模块概述

行业轮动分析模块提供两大核心能力：

1. **行业轮动分析 (Sector Rotation)** — 追踪 11 大 GICS 行业板块的资金流向、相对强弱及轮动趋势
2. **资本结构分析 (Capital Structure)** — 分析个股的资本结构阶段、因子暴露及信号识别

两个服务协同工作：行业轮动帮助确定宏观方向，资本结构帮助个股选择。

---

## 2. SectorRotationService

**文件**: `app/services/sector_rotation_service.py` (~340 lines)

### 2.1 主要方法

| 方法 | 说明 |
|------|------|
| `get_rotation_overview()` | 获取所有行业的轮动概览，包含各周期动量 |
| `get_sector_detail(name)` | 获取单个行业的详细分析，包含成分股表现 |
| `get_heatmap_data()` | 生成热力图矩阵数据 (行业 x 时间周期) |
| `get_top_sectors(n)` | 获取综合排名前 N 的行业 |
| `get_bottom_sectors(n)` | 获取综合排名后 N 的行业 |
| `get_available_sectors()` | 返回所有可用行业列表及其 ETF 代理 |

### 2.2 计算逻辑

行业强弱排名基于多周期加权动量：

```
综合评分 = 0.4 x 短期动量(1M) + 0.35 x 中期动量(3M) + 0.25 x 长期动量(6M)
```

每个周期的动量通过对应行业 ETF 的收益率计算：

| 行业 | 代理 ETF | 行业 | 代理 ETF |
|------|---------|------|---------|
| Technology | XLK | Materials | XLB |
| Healthcare | XLV | Utilities | XLU |
| Financials | XLF | Real Estate | XLRE |
| Energy | XLE | Communication Services | XLC |
| Consumer Discretionary | XLY | Industrials | XLI |
| Consumer Staples | XLP | | |

---

## 3. CapitalStructureService

**文件**: `app/services/capital_structure_service.py` (~275 lines)

### 3.1 主要方法

| 方法 | 说明 |
|------|------|
| `analyze(ticker)` | 综合分析：资本结构 + 阶段 + 因子 + 信号 |
| `get_factor_exposure(ticker)` | 计算个股在 5 大因子上的暴露度 |
| `get_capital_stage(ticker)` | 判断企业资本周期阶段 |
| `get_all_stages()` | 返回所有阶段定义及特征描述 |
| `get_signals(ticker)` | 基于资本结构生成交易信号 |

### 3.2 资本生命周期阶段

| 阶段 | 英文 | 特征 |
|------|------|------|
| 初创扩张 | Startup/Expansion | 高股权融资、低利润、高增长 |
| 成长加速 | Growth Acceleration | 营收快速增长、开始盈利 |
| 成熟稳定 | Mature/Stable | 稳定现金流、适度杠杆 |
| 现金牛 | Cash Cow | 高自由现金流、回购分红 |
| 衰退重组 | Decline/Restructuring | 收入下降、债务压力 |

### 3.3 五大因子暴露

- **Value Factor**: P/E, P/B, EV/EBITDA
- **Growth Factor**: Revenue Growth, Earnings Growth
- **Quality Factor**: ROE, Debt/Equity, Free Cash Flow Margin
- **Momentum Factor**: 价格动量 (3M, 6M, 12M)
- **Size Factor**: 市值 (Market Cap)

---

## 4. 行业分类映射

**文件**: `data/sector_mappings.py` (~292 lines)

```python
SECTOR_MAPPINGS = {
    "Technology": {
        "etf": "XLK",
        "stocks": ["AAPL", "MSFT", "NVDA", "GOOG", ...],
        "description": "信息技术行业",
        "sub_sectors": ["Software", "Semiconductors", "Hardware", ...]
    },
    # ... 11 个行业板块
}
```

辅助函数: `get_sector_for_ticker()`, `get_sector_etf()`, `get_all_sector_names()`, `get_stocks_in_sector()`

---

## 5. Sector Rotation API 端点

所有端点挂载在 Blueprint 下，前缀为 `/api/sector`。

### 5.1 GET /api/sector/rotation/overview

获取全部行业的轮动概览。返回各行业短/中/长期动量、综合评分、排名。结果缓存 15 分钟。

### 5.2 GET /api/sector/rotation/sector/{name}

获取单个行业的详细分析。Path Param `name` 为行业名称 (e.g. `Technology`)。
返回行业动量详情、成分股涨跌幅、行业新闻摘要。

### 5.3 GET /api/sector/rotation/heatmap

获取行业热力图数据。返回二维矩阵 — 行业 x 时间维度 (1D, 1W, 1M, 3M, 6M, 1Y)。

### 5.4 GET /api/sector/rotation/top-sectors

获取排名最高的行业。Query Param `n` (默认 3)。

### 5.5 GET /api/sector/rotation/bottom-sectors

获取排名最低的行业。Query Param `n` (默认 3)。

### 5.6 GET /api/sector/rotation/available-sectors

获取所有可分析的行业列表。返回行业名称、代理 ETF、成分股数量。

---

## 6. Capital Structure API 端点

前缀为 `/api/sector/capital`。

### 6.1 GET /api/sector/capital/analysis/{ticker}

获取个股综合资本结构分析。返回资本结构数据、生命周期阶段、因子暴露、信号列表。

### 6.2 GET /api/sector/capital/factor/{ticker}

获取个股的因子暴露度。返回 5 大因子的暴露值及百分位排名。

### 6.3 GET /api/sector/capital/stage/{ticker}

获取个股当前所处的资本生命周期阶段。返回阶段名称、置信度、关键指标。

### 6.4 GET /api/sector/capital/stages

获取所有资本生命周期阶段的定义。返回阶段列表，含定义、特征描述、典型指标范围。

### 6.5 GET /api/sector/capital/signals/{ticker}

获取基于资本结构分析的交易信号。返回信号列表，含方向 (bullish/bearish)、强度、依据。

---

## 7. 文件路径清单

| 文件路径 | 说明 | 大致行数 |
|---------|------|---------|
| `app/services/sector_rotation_service.py` | 行业轮动核心服务 | ~340 |
| `app/services/capital_structure_service.py` | 资本结构分析服务 | ~275 |
| `data/sector_mappings.py` | 行业分类映射数据 | ~292 |
| `app/routes/sector_routes.py` | Sector API 路由定义 | ~150 |

---

## 8. 注意事项

- 行业 ETF 数据通过 DataProvider 获取，遵循相同的缓存和 fallback 策略
- 热力图数据计算量较大，建议前端做适当缓存
- 资本结构分析依赖财务数据，部分小盘股可能数据不全
- 因子暴露的百分位排名基于同行业对比
