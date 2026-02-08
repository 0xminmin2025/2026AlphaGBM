# Auth & User 模块

## 1. 模块概述

认证与用户模块负责处理所有请求的身份验证和用户生命周期管理。

**核心架构决策：**

- 认证由 **Supabase Auth** 托管，后端不存储密码
- 前端获取 JWT token，每次请求通过 `Authorization: Bearer <token>` 传递
- 后端通过 `supabase.auth.get_user(token)` 验证 token 有效性
- 验证通过后，自动在本地数据库同步/创建 User 记录（Supabase UUID 作为主键）

**请求认证流程：**

```
Client Request
  │
  ├─ Authorization header 缺失 → 401
  │
  ├─ header 格式非 "Bearer <token>" → 401
  │
  ├─ token_cache 命中 (TTL < 5min)
  │     └─ 直接使用缓存 user → 跳过 Supabase 调用
  │
  └─ token_cache 未命中
        ├─ supabase.auth.get_user(token) 验证
        │     ├─ 成功 → 缓存 token, 同步本地 User
        │     ├─ SSL/timeout/connection error → 503 (最多重试 2 次)
        │     └─ 其他错误 → 401
        └─ 设置 Flask g 上下文 (g.user_id, g.user_email)
```

---

## 2. 核心组件

### 2.1 `@require_auth` 装饰器

文件：`app/utils/auth.py`，第 77-166 行

所有需要登录的 API 端点都通过此装饰器保护。完整处理逻辑：

```python
@require_auth
def protected_endpoint():
    # g.user_id 和 g.user_email 已可用
    ...
```

**Token 提取：** 从 `Authorization` header 按空格分割取第二段。header 缺失或格式不正确直接返回 `401`。

**Supabase 客户端初始化：** 模块加载时检查 `Config.SUPABASE_URL` 和 `Config.SUPABASE_KEY`。凭证齐全则调用 `create_client()` 初始化；缺失则 `supabase = None`，所有受保护端点返回 `500`。

**重试机制（缓存未命中时）：**

| 参数 | 值 |
|------|-----|
| max_retries | 2（共 3 次尝试） |
| base delay | 0.5s |
| 退避策略 | `retry_delay * (attempt + 1)`，即 0.5s → 1.0s → 1.5s |
| 网络错误 (SSL/timeout/connection) | 返回 503 Service Unavailable |
| 其他验证失败 | 返回 401 Invalid token |

**自动用户创建（第 142-159 行）：**

```python
existing_user = User.query.filter_by(id=user.id).first()
if not existing_user:
    new_user = User(id=user.id, email=user.email)
    db.session.add(new_user)
    db.session.commit()
else:
    # 仅在缓存未命中时更新 last_login（避免频繁 DB 写入）
    if not cached_user:
        existing_user.last_login = datetime.utcnow()
        db.session.commit()
```

**Flask g 上下文注入：**

```python
g.user_id = user.id        # Supabase UUID string
g.user_email = user.email   # 仅在 user 对象有 email 属性时设置
```

---

### 2.2 Token 缓存系统

文件：`app/utils/auth.py`，第 13-75 行。使用进程内 dict 缓存已验证的 token，避免每次请求都调用 Supabase API。

**数据结构：**

```python
token_cache = {}
# 格式: {token_string: {'user_data': user_obj, 'expires_at': timestamp}}
CACHE_DURATION = 300  # 5 分钟
```

**缓存函数一览：**

| 函数 | 作用 |
|------|------|
| `get_cached_user(token)` | 查找 token 对应缓存，过期则删除并返回 None |
| `cache_user_token(token, user_data)` | 存入缓存，设置 `expires_at = now + 300s` |
| `clean_expired_tokens()` | 遍历删除所有过期条目 |
| `invalidate_token_cache(token=None)` | 删除指定 token 缓存；无参数时清空全部 |

**自动清理触发条件：**

在 `cache_user_token()` 中，每 50 次写入触发一次 `clean_expired_tokens()`：

```python
if len(token_cache) % 50 == 0:
    clean_expired_tokens()
```

> 注意：这是进程内 dict，多 worker 部署时各 worker 独立维护缓存。

---

### 2.3 辅助函数

文件：`app/utils/auth.py`，第 168-186 行

```python
def get_user_id():
    """从 Flask g 安全提取 user_id，异常时返回 None"""
    return getattr(g, 'user_id', None)

def get_current_user_info():
    """返回 {'user_id': ..., 'email': ...} 或 None"""
    if hasattr(g, 'user_id'):
        info = {'user_id': g.user_id}
        if hasattr(g, 'user_email'):
            info['email'] = g.user_email
        return info
    return None
```

这两个函数供其他模块调用，无需直接访问 `g` 对象。

---

## 3. User 模型

文件：`app/models.py`，第 50-66 行

```python
class User(db.Model):
    id           = db.Column(db.String(36), primary_key=True)     # Supabase UUID
    email        = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username     = db.Column(db.String(80), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_login   = db.Column(db.DateTime, nullable=True)

    # Payment
    stripe_customer_id = db.Column(db.String(255), index=True, nullable=True)
    referrer_id        = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)

    # Relationships
    referrer           = db.relationship('User', remote_side=[id], backref='referrals')
    analysis_requests  = db.relationship('AnalysisRequest', backref='user', lazy=True)
    feedbacks          = db.relationship('Feedback', backref='user', lazy=True)
    daily_queries      = db.relationship('DailyQueryCount', backref='user', lazy=True)
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36), PK | 直接使用 Supabase UUID，非自增 |
| `email` | String(120), unique, indexed | 用户邮箱，唯一约束 |
| `username` | String(80), nullable | 可选用户名 |
| `stripe_customer_id` | String(255), indexed | Stripe 客户 ID，支付模块使用 |
| `referrer_id` | String(36), FK → user.id | 自引用外键，推荐人 |
| `created_at` | DateTime | 本地记录创建时间 |
| `last_login` | DateTime, nullable | 最后登录时间，仅缓存未命中时更新 |

**关联关系：**

- `referrer` / `referrals` — 自引用，推荐人与被推荐人
- `analysis_requests` — AnalysisRequest 分析请求记录
- `feedbacks` — Feedback 用户反馈
- `daily_queries` — DailyQueryCount 每日查询计数

---

## 4. API 端点

### 4.1 Auth Blueprint

文件：`app/api/auth.py`（8 行）

```python
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
```

| 方法 | 路径 | 认证 | 响应 |
|------|------|------|------|
| GET | `/api/auth/status` | 无 | `{'status': 'ok'}` |

健康检查端点，前端用于确认后端服务可用。

### 4.2 User Blueprint

文件：`app/api/user.py`（11 行）

```python
user_bp = Blueprint('user', __name__, url_prefix='/api/user')
```

| 方法 | 路径 | 认证 | 响应 |
|------|------|------|------|
| GET | `/api/user/profile` | `@require_auth` | `{'message': 'User Profile Endpoint'}` |

受保护端点示例，import 了 `require_auth` 和 `get_current_user_info`。

---

## 5. 安全机制

### Token 缓存防刷

- 同一 token 在 5 分钟内仅触发一次 Supabase API 调用
- 缓存命中时不更新 `last_login`，降低数据库写入压力
- 每 50 次缓存写入自动触发过期条目清理

### Supabase 客户端 Graceful Fallback

- 启动时若 `SUPABASE_URL` 或 `SUPABASE_KEY` 缺失，`supabase` 设为 `None`
- 此时所有 `@require_auth` 端点返回 `500 Supabase client not initialized`
- 不会因初始化失败导致进程崩溃

### 网络容错

- SSL、timeout、connection 错误返回 `503`（非 `401`），提示客户端可重试
- 指数退避重试，避免瞬时网络抖动导致认证失败

---

## 6. 文件路径清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `app/utils/auth.py` | 186 | `@require_auth` 装饰器、token 缓存、辅助函数 |
| `app/api/auth.py` | 8 | Auth Blueprint，`/api/auth/status` 端点 |
| `app/api/user.py` | 11 | User Blueprint，`/api/user/profile` 端点 |
| `app/models.py` | 428 | User 模型定义（第 50-66 行） |
