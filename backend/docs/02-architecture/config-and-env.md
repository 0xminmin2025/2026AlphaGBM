# 配置系统与环境变量

> 源文件: `backend/app/config.py`
> 模板文件: `backend/.env.example`

AlphaGBM 后端通过 `Config` 类集中管理所有运行时配置。启动时使用 `python-dotenv`
从 `backend/.env` 加载环境变量，未设置的变量使用内置默认值。

---

## 1. 环境变量完整清单

### 1.1 数据库

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_URL` | 生产必填 | -- | Supabase Connection Pooler URL（优先读取） |
| `SQLALCHEMY_DATABASE_URI` | 否 | -- | 备用数据库连接 URL；当 `POSTGRES_URL` 未设置时使用 |
| `DATABASE_DEBUG` | 否 | `false` | 设为 `true` 时输出所有 SQL 语句（SQLAlchemy echo） |

> 若两个数据库 URL 均未设置，自动 fallback 到本地 SQLite `backend/data/alphag.db`。

### 1.2 认证

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | 生产必填 | `dev-secret-key` | JWT 签名密钥；**生产环境必须替换** |
| `SUPABASE_URL` | 是 | -- | Supabase 项目 URL |
| `NEXT_PUBLIC_SUPABASE_URL` | 否 | -- | 前端同名变量，作为 `SUPABASE_URL` 的 fallback |
| `SUPABASE_ANON_KEY` | 是 | -- | Supabase 匿名公钥 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | 否 | -- | 前端同名变量，作为 `SUPABASE_ANON_KEY` 的 fallback |
| `SUPABASE_KEY` | 否 | -- | 第三级 fallback（兼容旧配置） |

### 1.3 支付 (Stripe)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | 是 | `''` | Stripe Secret Key |
| `STRIPE_WEBHOOK_SECRET` | 是 | `''` | Stripe Webhook 签名密钥 |
| `STRIPE_PRICE_PLUS_MONTHLY` | 是 | `''` | Plus 月付 Price ID |
| `STRIPE_PRICE_PLUS_YEARLY` | 是 | `''` | Plus 年付 Price ID |
| `STRIPE_PRICE_PRO_MONTHLY` | 是 | `''` | Pro 月付 Price ID |
| `STRIPE_PRICE_PRO_YEARLY` | 是 | `''` | Pro 年付 Price ID |
| `STRIPE_PRICE_TOPUP_100` | 是 | `''` | 加油包 (Top-up 100) Price ID |

### 1.4 AI

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | 是 | `''` | Google Gemini API 密钥，用于图像识别等 AI 功能 |

### 1.5 数据源

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TIGER_ID` | 否 | -- | Tiger Open API ID（通过 properties 文件配置） |
| `TIGER_PRIVATE_KEY` | 否 | -- | Tiger 私钥（通过 properties 文件配置） |
| `TUSHARE_TOKEN` | 否 | `''` | Tushare Pro API 令牌，A 股数据源 |
| `ALPHA_VANTAGE_API_KEY` | 否 | `''` | Alpha Vantage API 密钥，美股补充数据源 |

> **Tiger 说明**: Tiger API 使用 `tiger_openapi_config.properties` 文件进行认证，
> 搜索路径依次为: `backend/tiger_openapi_config.properties` -> `/etc/tiger/` 等。
> 未找到配置文件时该 provider 自动禁用。

### 1.6 飞书

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FEISHU_WEBHOOK_URL` | 否 | `''` | 飞书机器人 Webhook URL，用于每日运营数据推送 |

### 1.7 邮件

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAIL_SERVER` | 否 | `smtp.gmail.com` | SMTP 服务器地址 |
| `MAIL_PORT` | 否 | `587` | SMTP 端口 |
| `MAIL_USE_TLS` | 否 | `True` | 是否启用 TLS 加密 |
| `MAIL_USERNAME` | 否 | `''` | SMTP 登录用户名 |
| `MAIL_PASSWORD` | 否 | `''` | SMTP 登录密码 |
| `MAIL_DEFAULT_SENDER` | 否 | 同 `MAIL_USERNAME` | 默认发件人地址 |

### 1.8 业务逻辑

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REGULAR_USER_DAILY_MAX_QUERIES` | 否 | `2` | 免费用户每日最大查询次数（股票 + 期权共享） |

---

## 2. Config 类结构

### 2.1 .env 加载

```python
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '../.env')  # backend/.env
load_dotenv(DOTENV_PATH)
```

启动时从 `backend/.env` 读取所有键值对，注入到 `os.environ` 中。

### 2.2 数据库 URL 优先级

```
POSTGRES_URL  -->  SQLALCHEMY_DATABASE_URI  -->  SQLite fallback
   (1st)                 (2nd)                  (backend/data/alphag.db)
```

### 2.3 URL 清洗

连接 URL 在使用前会进行两步清洗:

1. **Scheme 修正**: `postgres://` 替换为 `postgresql://`（SQLAlchemy 要求）
2. **参数清理**: 移除 Supabase 注入的 `supa` query parameter（psycopg2 不识别）

### 2.4 PostgreSQL 连接池参数

| Parameter | Value | Description |
|-----------|-------|-------------|
| `pool_size` | 10 | 连接池常驻连接数 |
| `max_overflow` | 20 | 超出 pool_size 时允许的额外连接数 |
| `pool_timeout` | 30s | 从池中获取连接的等待超时 |
| `pool_recycle` | 300s (5min) | 连接回收周期（Supabase 必须设置较短值） |
| `pool_pre_ping` | True | 每次使用前验证连接是否存活 |

**PostgreSQL connect_args:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `connect_timeout` | 10s | TCP 连接超时 |
| `application_name` | `AlphaG-Backend` | 数据库监控中显示的应用名 |
| `statement_timeout` | 30000ms (30s) | 单条 SQL 语句的执行超时 |
| `keepalives` | 1 | 启用 TCP keepalive |
| `keepalives_idle` | 60s | 空闲多久后发送 keepalive |
| `keepalives_interval` | 10s | keepalive 探测间隔 |
| `keepalives_count` | 5 | 失败几次后判定连接死亡 |

### 2.5 SQLite 连接池参数 (fallback)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `pool_size` | 5 | 较小的连接池 |
| `max_overflow` | 10 | 有限的溢出连接 |
| `pool_timeout` | 20s | 较短的等待超时 |
| `pool_recycle` | 1800s (30min) | 较长的回收周期（本地无网络问题） |
| `pool_pre_ping` | False | SQLite 无需预检 |

**SQLite connect_args:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `check_same_thread` | False | 允许 SQLite 多线程访问 |
| `timeout` | 20s | SQLite 锁等待超时 |

---

## 3. 安全说明

### 3.1 敏感变量（不可泄露）

以下变量包含密钥或凭证，**严禁出现在日志、前端响应、Git 仓库中**:

- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET`
- `POSTGRES_URL` / `SQLALCHEMY_DATABASE_URI`（包含数据库密码）
- `GOOGLE_API_KEY`
- `TUSHARE_TOKEN`
- `ALPHA_VANTAGE_API_KEY`
- `JWT_SECRET_KEY`
- `MAIL_PASSWORD`
- `FEISHU_WEBHOOK_URL`（可被用于发送消息）
- `SUPABASE_ANON_KEY`（虽为"匿名"密钥，仍应保护不被滥用）

### 3.2 开发默认值

`JWT_SECRET_KEY` 的默认值 `dev-secret-key` **仅用于本地开发**。
生产环境部署时必须设置为高强度随机字符串，否则 JWT 签名可被伪造。

### 3.3 .env.example 模板

`backend/.env.example` 提供了所有可配置变量的模板。新开发者应:

1. 复制 `backend/.env.example` 为 `backend/.env`
2. 填入实际的密钥和连接信息
3. 确保 `.env` 已被 `.gitignore` 排除（不可提交到版本控制）

```bash
cp backend/.env.example backend/.env
# 编辑 .env 填入实际值
```

### 3.4 Stripe Price ID 说明

`STRIPE_PRICES` 字典将 5 个价格 ID 映射为内部键名:

```python
STRIPE_PRICES = {
    'plus_monthly':  STRIPE_PRICE_PLUS_MONTHLY,
    'plus_yearly':   STRIPE_PRICE_PLUS_YEARLY,
    'pro_monthly':   STRIPE_PRICE_PRO_MONTHLY,
    'pro_yearly':    STRIPE_PRICE_PRO_YEARLY,
    'topup_100':     STRIPE_PRICE_TOPUP_100,
}
```

Price ID 从 Stripe Dashboard 获取，格式为 `price_xxxxxxxxxxxxxxxx`。
若未配置，对应订阅/购买功能将不可用。

---

## 4. 配置加载流程图

```
App 启动
  |
  v
load_dotenv("backend/.env")          # 加载 .env 到 os.environ
  |
  v
Config 类属性求值                      # 读取 os.getenv + 默认值
  |
  +---> POSTGRES_URL 存在?
  |       |
  |       Yes --> 清洗 URL --> PostgreSQL engine options
  |       No  --> SQLALCHEMY_DATABASE_URI 存在?
  |                 |
  |                 Yes --> 清洗 URL --> PostgreSQL engine options
  |                 No  --> SQLite fallback --> SQLite engine options
  |
  v
Flask app.config.from_object(Config)  # 注入到 Flask
```
