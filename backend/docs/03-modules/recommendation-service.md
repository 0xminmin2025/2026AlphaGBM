# 每日期权推荐服务 (Recommendation Service)

## 1. 模块概述

**文件**: `app/services/recommendation_service.py` (717 行)

每日期权推荐服务是系统的主动推荐引擎，定期扫描热门标的的期权链，自动筛选并排序最佳期权交易机会。核心设计理念基于用户实战经验：

- **标的选择很重要**：不以接股为目的的 Sell Put 都是乱来
- **时机选择**：最好在股票下跌时卖更低价格的 Put
- **日权风险**：日权（0DTE）不适合 Sell Put 策略

采用 **DB 缓存 + 按需刷新** 模式，每日首次请求时生成推荐，后续直接返回缓存。

---

## 2. RecommendationService 类

```python
class RecommendationService:
    def __init__(self):
        self.scorer = OptionScorer()          # 期权评分器
        self._price_trend_cache = {}          # 价格趋势内存缓存（1hr TTL）
```

**热门标的**: `HOT_SYMBOLS = ['SPY', 'QQQ', 'IWM', 'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'AMD']`，实际分析取前 8 个。

---

## 3. 推荐流程

```
get_daily_recommendations(count=5, force_refresh=False)
│
├── 检查 DailyRecommendation DB 缓存
│   └── 命中 → 返回 cached.recommendations[:count]
│
└── _generate_recommendations(count)
    ├── for symbol in HOT_SYMBOLS[:8]:
    │   └── _analyze_symbol(symbol)
    │       ├── DataProvider → current_price, expiry_dates[:5]
    │       ├── 排除日权（today/tomorrow 到期）→ filtered[:3]
    │       ├── get_symbol_quality_score() → tier & quality
    │       ├── get_price_trend() → trend & change_pct
    │       └── per expiry: option_chain → _score_options()
    │           ├── 筛选虚值（PUT: <0.98x, CALL: >1.02x）
    │           ├── OptionScorer.score_option() → sprv/scrv/bcrv/bprv
    │           ├── 选最佳策略（阈值 MIN_SCORE=20）
    │           └── calculate_timing_bonus() → 0-10 加分
    ├── 按 score 降序 → _ensure_diversity(max 2/strategy)
    ├── _generate_market_summary()
    └── _save_to_cache() → DailyRecommendation DB
```

---

## 4. 标的质量评分 `get_symbol_quality_score()`

核心原则：**选择愿意接股、接了后有信心涨回去的标的**。

| Tier | 类别 | Quality | 代表标的 |
|------|------|---------|----------|
| **1** | 蓝筹 ETF | 85-95 | SPY(95), QQQ(90), IWM(85), DIA(92), VOO(95) |
| **2** | 大盘蓝筹 | 80-90 | MSFT(90), AAPL(88), BRK-B(88), GOOGL(85) |
| **3** | 高成长股 | 70-80 | NVDA(80), META(78), CRM(76), AMD(75), TSLA(70) |
| **4** | 高风险标的 | 40-55 | COIN(55), MSTR(50), GME(40), AMC(40) |
| **5** | 未评级 | 50 | 其他所有标的（默认） |

---

## 5. 趋势分析 `get_price_trend()`

```python
hist = DataProvider(symbol).history(period=f"{days+2}d")    # 默认 days=5
change_pct = (last_close - first_close) / first_close * 100

change < -3%  → trend='down',     good_for_put=True
change > +3%  → trend='up',       good_for_put=False
else          → trend='sideways',  good_for_put=True
```

- **缓存**: `{symbol}_{days}` 为 key，**1 小时** TTL，内存 dict

---

## 6. 时机奖励 `calculate_timing_bonus()`

| 策略 | 趋势 | 加分公式 | 范围 |
|------|------|----------|------|
| `sell_put` | down | `min(10, abs(change_pct) * 2)` | 0-10 |
| `sell_call` | up | `min(10, abs(change_pct) * 2)` | 0-10 |
| `sell_*` | sideways | 固定 3 | 3 |
| 其他 | - | 0 | 0 |

---

## 7. 多样性 `_ensure_diversity()`

- 每种策略最多 **2 个**推荐（`sell_put`, `sell_call`, `buy_call`, `buy_put`）
- 输入已按 score 降序，贪心选择直到达到 count

---

## 8. 市场摘要 `_generate_market_summary()`

| 字段 | 说明 |
|------|------|
| `overall_trend` | `range_bound`（卖方主导）/ `trending`（买方主导）/ `mixed` |
| `recommended_strategies` | 出现次数最多的前 2 种策略 |
| `avg_iv_rank` | 平均 IV Rank |
| `strategy_distribution` | 各策略数量统计 |

判断：`sell_count > buy_count * 1.5` → range_bound; 反之 → trending; 否则 mixed。

---

## 9. 缓存机制

| 层 | 模型/存储 | TTL | 失效方式 |
|----|----------|-----|----------|
| DB 缓存 | `DailyRecommendation`（recommendation_date, recommendations JSON, market_summary JSON） | 当日 | 次日自动过期 / `force_refresh=True` |
| 内存缓存 | `_price_trend_cache` dict | 1 小时 | 自动过期 |

`_save_to_cache()` 采用 upsert 语义：存在则更新，不存在则新建。

---

## 10. 文件路径

| 文件 | 职责 |
|------|------|
| `backend/app/services/recommendation_service.py` | 推荐服务主逻辑（717 行） |
| `backend/app/services/option_scorer.py` | 期权评分器 |
| `backend/app/services/option_models.py` | OptionData 数据模型 |
| `backend/app/services/data_provider.py` | 统一数据源（yfinance + defeatbeta fallback） |
| `backend/app/models.py` | DailyRecommendation DB 模型 |

---

*文档版本: 2026.02 | 基于 recommendation_service.py 实际代码编写*
