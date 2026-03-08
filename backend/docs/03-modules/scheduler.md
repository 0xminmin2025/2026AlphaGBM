# Scheduler 模块

## 1. 模块概述

调度模块基于 APScheduler 的 `BackgroundScheduler` 实现后台定时任务，负责每日自动化运维操作。

**文件**: `app/scheduler.py` (~276 lines)

**核心定时任务**:

| 任务 | 触发时间 (UTC) | 说明 |
|------|---------------|------|
| `calculate_daily_profit_loss` | 每日 18:12 | 计算持仓每日 P&L |
| `send_daily_report` | 每日 20:00 | 发送每日运营报告 (飞书机器人) |

---

## 2. 定时任务详情

### 2.1 calculate_daily_profit_loss

**触发时间**: UTC 18:12 (约北京时间次日 02:12，美东 14:12 — 美股收盘后)

**执行流程**:

```
Step 1: 获取当前日期,检查 DailyProfitLoss 表是否已有当日记录 (跳过已计算)
Step 2: 查询所有 PortfolioHolding 记录 (无持仓则退出)
Step 3: 调用 get_exchange_rates() 获取当前汇率
Step 4: 遍历每个持仓:
        a. get_current_stock_price(ticker) 获取当前价格
        b. 获取失败则使用 buy_price 作为 fallback
        c. 计算 current_value = shares x current_price
        d. 调用 convert_to_usd() 统一转为 USD
Step 5: 按 style 维度汇总 (value/growth/speculative/hedge)
Step 6: 写入 StyleProfit 记录 (每个 style 一条)
Step 7: 写入 DailyProfitLoss 汇总记录
Step 8: db.session.commit() 提交事务
```

### 2.2 send_daily_report

**触发时间**: UTC 20:00 (北京时间次日 04:00)

通过飞书 (Feishu/Lark) Webhook 机器人推送每日运营数据：当日分析请求量、活跃用户数、持仓盈亏概览、系统健康指标。

---

## 3. 汇率服务

### 3.1 get_exchange_rates()

从 exchangerate-api.com 获取实时汇率数据。

**API 端点**: `https://api.exchangerate-api.com/v4/latest/USD`

**缓存机制**: 1 小时内存缓存，module-level 变量存储，进程内共享。

```python
_exchange_rate_cache = {'rates': None, 'timestamp': None}
_CACHE_DURATION = timedelta(hours=1)
```

**Fallback rates** (API 不可用时):

| 货币 | 兑 USD 汇率 |
|------|------------|
| `HKD` | 7.8 |
| `CNY` | 7.2 |

---

## 4. 股价获取

### 4.1 get_current_stock_price(ticker)

通过 DataProvider 获取股票当前价格，带多字段 fallback 逻辑：

```
regularMarketPrice -> currentPrice -> previousClose -> None
```

返回 None 时，P&L 计算使用 buy_price 作为当前价 (盈亏为 0)。
异常处理：网络超时记录 warning，数据解析失败记录 error。

---

## 5. P&L 计算细节

### 5.1 跳过已计算日

```python
existing = DailyProfitLoss.query.filter_by(date=today).first()
if existing:
    logger.info(f"P&L already calculated for {today}")
    return
```

### 5.2 按 Style 汇总

```python
for style in ['value', 'growth', 'speculative', 'hedge']:
    style_data = styles_data.get(style, {'value': 0, 'cost': 0})
    profit_loss = style_data['value'] - style_data['cost']
    profit_loss_pct = (profit_loss / style_data['cost'] * 100) if style_data['cost'] > 0 else 0
    style_record = StyleProfit(date=today, style=style, ...)
    db.session.add(style_record)
```

### 5.3 写入 DailyProfitLoss

```python
daily = DailyProfitLoss(
    date=today,
    total_value_usd=total_value,
    total_cost_usd=total_cost,
    total_profit_loss=total_value - total_cost,
    total_profit_loss_pct=((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
)
db.session.add(daily)
db.session.commit()
```

---

## 6. init_scheduler(app)

调度器初始化函数，在 Flask app 启动时调用。

### 6.1 WERKZEUG_RUN_MAIN Guard

Flask 开发模式下 Werkzeug 会 fork 子进程，为防止调度器初始化两次：

```python
def init_scheduler(app):
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true' and app.debug:
        return
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: run_with_app_context(app, calculate_daily_profit_loss),
        trigger=CronTrigger(hour=18, minute=12),
        id='daily_profit_loss', replace_existing=True
    )
    scheduler.add_job(
        func=lambda: run_with_app_context(app, send_daily_report),
        trigger=CronTrigger(hour=20, minute=0),
        id='daily_report', replace_existing=True
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
```

### 6.2 atexit 清理

注册 `atexit` 回调确保进程退出时优雅关闭调度器，等待当前任务完成并释放线程资源。

---

## 7. run_with_app_context(app, func)

Flask 应用上下文包装器。APScheduler 的 worker 线程不在 Flask 请求上下文中，但数据库操作需要 app context。

```python
def run_with_app_context(app, func):
    with app.app_context():
        try:
            func()
        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")
            db.session.rollback()
```

所有定时任务通过此 wrapper 执行，异常自动捕获，数据库异常时执行 `rollback()` 防止连接泄漏。

---

## 8. 文件路径清单

| 文件路径 | 说明 | 大致行数 |
|---------|------|---------|
| `app/scheduler.py` | 调度器核心 + P&L 计算 + 汇率服务 | ~276 |
| `app/models/portfolio.py` | DailyProfitLoss, StyleProfit 模型 | ~120 |
| `app/services/data_provider.py` | DataProvider (股价获取) | ~400 |

---

## 9. 注意事项

- UTC 时间配置: 所有 CronTrigger 使用 UTC 时间，部署时无需考虑时区
- 重复执行保护: `calculate_daily_profit_loss` 内置去重逻辑
- 内存缓存: 汇率缓存为进程级别，多进程部署时每个进程独立缓存
- Fallback 汇率: 仅在 API 不可用时使用，生产环境应监控此告警
- 数据库事务: 单次计算为一个事务，失败时整体回滚
