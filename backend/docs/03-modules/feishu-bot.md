# 飞书机器人推送服务 (Feishu Bot)

## 1. 模块概述

**文件**: `app/services/feishu_bot.py` (153 行)

飞书自定义机器人 Webhook 推送服务，每日自动推送运营数据报告到飞书群。报告包含三大维度：**用户数据**、**付费数据**、**收入数据**。模块采用纯函数设计，由三个核心函数组成。

---

## 2. `get_daily_stats()` -- 数据查询

查询今日及累计运营数据，返回统计字典。

| 指标 | 查询方式 | 数据源 |
|------|----------|--------|
| 今日新增用户 | `User.query.filter(created_at between today)` | `User.created_at` |
| 累计用户总数 | `User.query.count()` | `User` 表 |
| 今日新增付费 | `Subscription.filter(today, status='active')` | `Subscription` |
| 累计付费用户 | `count(distinct(user_id)).filter(status='active')` | `Subscription` |
| 今日收入 | `sum(amount).filter(status='succeeded', today)` | `Transaction` |
| 累计总收入 | `sum(amount).filter(status='succeeded')` | `Transaction` |

**金额处理**: `Transaction.amount` 以 cents 存储，除以 100 转 dollars。使用 `func.coalesce(..., 0)` 防止 `None`。

返回结构:

```python
{
    'date': '2026-02-08',
    'new_users_today': int, 'total_users': int,
    'new_paid_today': int,  'total_paid_users': int,
    'today_revenue': float, 'total_revenue': float,   # 美元
}
```

---

## 3. `build_card_message(stats)` -- 构建飞书卡片

将统计数据格式化为飞书 Interactive Card 消息。

```
+--------------------------------------+
| [蓝色 Header] AlphaGBM 每日运营报告    |
+--------------------------------------+
| 日期：2026-02-08                      |
+--------------------------------------+
| 用户数据: 新注册 5 / 累计 1,234       |
+--------------------------------------+
| 付费数据: 新付费 2 / 累计 89          |
+--------------------------------------+
| 收入数据: 今日 $49.90 / 累计 $12,345  |
+--------------------------------------+
```

- 消息类型: `msg_type: "interactive"`，Header template: `"blue"`
- 文本格式: `lark_md`（飞书 Markdown），`{"tag": "hr"}` 分节
- 数字格式化: 千分位 `{:,}`，金额 `${:,.2f}`

---

## 4. `send_daily_report()` -- 主发送函数

```
send_daily_report()
├── 读取 FEISHU_WEBHOOK_URL（未配置 → warn → return False）
├── get_daily_stats() → stats
├── build_card_message(stats) → payload
├── requests.post(webhook_url, json=payload, timeout=10)
└── resp.json().code == 0 → True; 否则 → False
```

错误处理: Webhook 未配置跳过; HTTP 异常捕获后 return False; 飞书 API 错误码记录 error log。

---

## 5. 触发方式

| 参数 | 值 |
|------|-----|
| 调度器 | APScheduler `CronTrigger` |
| 触发时间 | 每日 **20:00 UTC**（北京时间次日 04:00） |
| 环境变量 | `FEISHU_WEBHOOK_URL` |

---

## 6. 数据源模型

| 模型 | 关键字段 | 用途 |
|------|----------|------|
| `User` | `created_at` | 统计用户数 |
| `Subscription` | `user_id`, `status`, `created_at` | 付费用户（`status='active'`） |
| `Transaction` | `amount`(cents), `status`, `created_at` | 收入（`status='succeeded'`） |

---

## 7. 文件路径

| 文件 | 职责 |
|------|------|
| `backend/app/services/feishu_bot.py` | 飞书推送服务（153 行） |
| `backend/app/models.py` | User / Subscription / Transaction 模型 |
| `backend/app/scheduler.py` | 定时任务调度配置 |

---

*文档版本: 2026.02 | 基于 feishu_bot.py 实际代码编写*
