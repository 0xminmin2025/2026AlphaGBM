# Portfolio Management 模块

## 1. 模块概述

持仓管理模块负责管理用户的股票/期权持仓组合，并提供每日 P&L (Profit & Loss) 自动计算功能。
系统按照 4 种投资风格 (style) 对持仓进行分类：

| Style 标识 | 含义 | 典型持仓 |
|-----------|------|---------|
| `value` | 价值投资 | 蓝筹股、高股息股 |
| `growth` | 成长投资 | 高增长科技股 |
| `speculative` | 投机交易 | 短线波段、热点题材 |
| `hedge` | 对冲保护 | Put 保护、反向 ETF |

每日计算由 `scheduler.py` 中的定时任务触发，自动完成价格获取、汇率转换、盈亏计算及风格汇总。

---

## 2. 数据模型

### 2.1 PortfolioHolding

持仓记录主表，每条记录代表一个持仓头寸。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer, PK | 主键 |
| `ticker` | String(20) | 股票代码 (e.g. `AAPL`, `0700.HK`, `600519.SS`) |
| `shares` | Float | 持有股数 |
| `buy_price` | Float | 买入均价 (原始货币) |
| `style` | String(20) | 投资风格: `value` / `growth` / `speculative` / `hedge` |
| `currency` | String(3) | 货币代码: `USD` / `HKD` / `CNY` |
| `buy_date` | DateTime | 买入日期 |
| `notes` | Text | 备注信息 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

### 2.2 DailyProfitLoss

每日盈亏汇总记录，每天一条。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer, PK | 主键 |
| `date` | Date | 计算日期 |
| `total_value_usd` | Float | 持仓总市值 (USD) |
| `total_cost_usd` | Float | 持仓总成本 (USD) |
| `total_profit_loss` | Float | 总盈亏金额 (USD) |
| `total_profit_loss_pct` | Float | 总盈亏百分比 |
| `created_at` | DateTime | 创建时间 |

### 2.3 StyleProfit

按风格分类的每日盈亏明细。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer, PK | 主键 |
| `date` | Date | 计算日期 |
| `style` | String(20) | 投资风格 |
| `value_usd` | Float | 该风格持仓市值 (USD) |
| `cost_usd` | Float | 该风格持仓成本 (USD) |
| `profit_loss` | Float | 该风格盈亏 (USD) |
| `profit_loss_pct` | Float | 该风格盈亏百分比 |

### 2.4 PortfolioRebalance

再平衡操作记录，记录每次持仓调整。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer, PK | 主键 |
| `date` | DateTime | 操作日期 |
| `action` | String(10) | 操作类型: `buy` / `sell` / `adjust` |
| `ticker` | String(20) | 股票代码 |
| `shares` | Float | 操作股数 |
| `price` | Float | 操作价格 |
| `reason` | Text | 调整原因 |

---

## 3. 每日计算流程

由 `scheduler.py` 中的定时任务驱动，每日自动执行。

### 3.1 触发时间

- 定时任务设置为 **UTC 18:12** 触发 (对应美东收盘后)
- 使用 APScheduler 的 `CronTrigger` 配置

### 3.2 执行步骤

```
Step 1: 查询数据库获取所有 PortfolioHolding 记录
        ↓
Step 2: 检查当日是否已计算 (跳过已计算日期,防止重复)
        ↓
Step 3: 通过 DataProvider 获取每只股票的当前价格
        - 使用 get_current_stock_price() 方法
        - 多字段 fallback: regularMarketPrice → currentPrice → previousClose
        ↓
Step 4: 汇率转换 — 将 HKD/CNY 持仓统一转为 USD
        - 调用 get_exchange_rates() 获取实时汇率
        - 详见下方「汇率服务」章节
        ↓
Step 5: 逐只计算盈亏
        - profit_loss = (current_price - buy_price) × shares
        - profit_loss_pct = (current_price - buy_price) / buy_price × 100
        ↓
Step 6: 按 style 维度汇总,写入 StyleProfit 表
        ↓
Step 7: 汇总全部持仓,写入 DailyProfitLoss 表
```

---

## 4. API 端点

所有端点均无需认证 (no auth required)，挂载在 Blueprint `portfolio_bp` 下。

### 4.1 GET /api/portfolio/holdings

获取当前所有持仓列表。

- **Response**: 持仓数组，包含 ticker、shares、buy_price、style、currency、当前价、盈亏等
- **排序**: 按 style 分组，组内按市值降序

### 4.2 GET /api/portfolio/daily-stats

获取当日持仓统计概览。

- **Response**: 总市值、总成本、总盈亏、各风格占比
- **逻辑**: 实时计算，不依赖 DailyProfitLoss 表

### 4.3 GET /api/portfolio/profit-loss/history

获取历史盈亏记录。

- **Query Params**: `days` (默认 30，最大 365)
- **Response**: 按日期排序的 DailyProfitLoss 数组，包含 StyleProfit 明细

### 4.4 GET /api/portfolio/rebalance-history

获取再平衡操作历史。

- **Query Params**: `days` (默认 90)
- **Response**: PortfolioRebalance 记录数组

---

## 5. 汇率服务

### 5.1 get_exchange_rates()

从 exchangerate-api.com 获取实时汇率，转换为 USD 基准。

- **API 来源**: `https://api.exchangerate-api.com/v4/latest/USD`
- **缓存策略**: 1 小时内存缓存 (避免频繁请求)
- **Fallback rates** (API 不可用时的默认汇率):
  - `HKD`: 7.8 (1 USD = 7.8 HKD)
  - `CNY`: 7.2 (1 USD = 7.2 CNY)

```python
# 缓存结构
_exchange_rate_cache = {
    'rates': {...},
    'timestamp': datetime
}
_CACHE_DURATION = timedelta(hours=1)
```

### 5.2 convert_to_usd(amount, currency, rates)

将指定货币金额转换为 USD。

- 若 `currency == 'USD'`，直接返回
- 否则按 `amount / rates[currency]` 计算
- 未知货币按 1:1 处理并记录 warning 日志

---

## 6. 文件路径清单

| 文件路径 | 说明 | 大致行数 |
|---------|------|---------|
| `app/scheduler.py` | 定时任务调度 + P&L 计算逻辑 | ~276 |
| `app/models/portfolio.py` | PortfolioHolding, DailyProfitLoss 等模型 | ~120 |
| `app/routes/portfolio_routes.py` | Portfolio API 路由 | ~180 |
| `app/services/data_provider.py` | DataProvider 价格获取 | ~400 |

---

## 7. 注意事项

- P&L 计算会跳过已存在记录的日期，避免重复写入
- 港股代码格式遵循 Yahoo Finance 4 位标准 (e.g. `0700.HK`)
- 汇率 fallback 值为硬编码，仅在 API 完全不可用时启用
- 所有金额最终以 USD 为统一计量单位
- 日志中会记录每次计算的持仓数量、总市值及各风格汇总
