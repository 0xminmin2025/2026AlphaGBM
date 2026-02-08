# Backend 设计标准文档

> 本文档定义 AlphaG 后端系统的架构设计原则、编码规范与最佳实践。
> 迁移整合自 `docs/DESIGN_STANDARDS.md`，聚焦于 Backend 部分。

---

## 1. 架构设计原则

### 1.1 分层架构

系统采用五层架构，各层职责明确，禁止跨层调用：

```
Client Request → Route 层 → Middleware 层 → Service 层 → Analysis 层 → Data 层

Route 层       Flask Blueprints (api/*.py)       HTTP 解析、参数校验、响应序列化
Middleware 层  认证装饰器、限流中间件              JWT 验证、积分检查、Rate Limiting
Service 层    services/*.py                      编排分析流程、支付逻辑、任务调度
Analysis 层   analysis/stock_analysis/ 等        GBM 模型、Black-Scholes、评分算法
Data 层       models.py, data_provider.py        SQLAlchemy ORM、外部 API 数据获取
```

**调用规则**：
- Route 层只调用 Service 层，不直接调用 Analysis 或 Data 层
- Service 层编排 Analysis 层和 Data 层的调用
- Analysis 层通过 Data 层获取数据，不直接访问数据库

### 1.2 单一职责原则

| 模块 | 职责 | 反例 |
|------|------|------|
| `api/stock.py` | 股票相关 HTTP 端点 | 不应包含分析算法 |
| `services/analysis_engine.py` | 分析流程编排 | 不应处理 HTTP 请求 |
| `analysis/stock_analysis/` | 股票评分算法 | 不应直接读写数据库 |
| `services/payment_service.py` | 支付与积分逻辑 | 不应包含用户认证 |

### 1.3 依赖注入（工厂模式）

使用 Flask Application Factory 模式，通过 `create_app()` 初始化并注入依赖：

```python
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app)
    cors.init_app(app)
    # 注册 Blueprints
    from .api import stock, options, auth
    app.register_blueprint(stock.bp)
    return app
```

**禁止**在模块顶层创建全局有状态对象。所有外部依赖通过 `current_app` 或初始化函数注入。

---

## 2. 代码组织规范

### 2.1 文件命名

- Python 文件：`snake_case.py`（如 `analysis_engine.py`、`payment_service.py`）
- 测试文件：`test_<module_name>.py`
- 配置文件：`config.py`、`constants.py`

### 2.2 模块划分（按功能域）

```
backend/app/
├── api/                    # Route 层：auth, stock, options, payment, portfolio, sector, user
├── services/               # Service 层：analysis_engine, options_service, payment_service, data_provider, ai_service
├── analysis/               # Analysis 层：stock_analysis/, options_analysis/
├── models.py               # Data 层 — SQLAlchemy 模型
├── config.py               # 应用配置
├── constants.py            # 常量定义
└── utils/                  # 公共工具函数
```

### 2.3 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `StockAnalysisEngine` |
| 函数/方法 | snake_case | `calculate_risk_score()` |
| 变量 | snake_case | `current_price` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 私有方法 | 前缀单下划线 | `_internal_calculate()` |

### 2.4 导入顺序

每组之间空一行，组内按字母排序：

```python
# 1. 标准库
import os
from datetime import datetime

# 2. 第三方库
import numpy as np
from flask import Blueprint, request, jsonify

# 3. 本地模块
from app.models import StockAnalysisHistory
from app.services.analysis_engine import AnalysisEngine
```

### 2.5 文件大小

单文件建议不超过 500 行，超过时按子功能拆分。

---

## 3. API 设计标准

### 3.1 RESTful 规范

| HTTP Method | 用途 | 示例 |
|-------------|------|------|
| GET | 获取资源 | `GET /api/stock/history` |
| POST | 创建资源或执行操作 | `POST /api/stock/analyze` |
| PUT | 完整更新资源 | `PUT /api/user/profile` |
| DELETE | 删除资源 | `DELETE /api/stock/history/123` |

### 3.2 URL 设计

格式：`/api/{resource}/{action_or_id}`

示例：
- `GET /api/stock/history` — 获取分析历史
- `POST /api/stock/analyze` — 执行股票分析
- `POST /api/options/analyze` — 执行期权分析
- `POST /api/payment/create-checkout` — 创建支付会话

### 3.3 HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | 请求正常处理 |
| 201 | 创建成功 | 新资源创建完成 |
| 400 | 请求参数错误 | 缺少必填字段、格式不合法 |
| 401 | 未授权 | Token 缺失或无效 |
| 402 | 积分不足 | 用户余额不足 |
| 403 | 禁止访问 | 无权限 |
| 404 | 资源不存在 | 记录未找到 |
| 429 | 请求过于频繁 | Rate Limiting 触发 |
| 500 | 服务器内部错误 | 未预期异常 |

### 3.4 响应格式

**成功响应**：
```json
{
  "success": true,
  "data": { "ticker": "AAPL", "score": 8.5 },
  "remaining_credits": 150
}
```

**错误响应**：
```json
{ "error": "无效的股票代码", "code": "INVALID_TICKER" }
```

常见 Error Code：`INVALID_TICKER` | `INSUFFICIENT_CREDITS` | `ANALYSIS_FAILED` | `DATA_UNAVAILABLE` | `RATE_LIMITED`

### 3.5 请求认证

所有 API 端点（除 `/health`）均需 Bearer Token：
```
Authorization: Bearer <supabase_jwt_token>
```

---

## 4. 数据库设计规范

### 4.1 表命名

- snake_case 复数形式：`users`、`stock_analysis_history`
- 关联表：`user_subscriptions`、`credit_transactions`

### 4.2 字段命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 主键 | `id` | `db.Column(db.Integer, primary_key=True)` |
| 外键 | `{关联表}_id` | `user_id`、`stock_id` |
| 时间戳 | `{action}_at` | `created_at`、`updated_at` |
| 布尔值 | `is_` / `has_` 前缀 | `is_active`、`has_permission` |

### 4.3 索引规则

- 所有外键字段必须建索引
- 常查询字段（`ticker`、`created_at`）必须建索引
- 多字段联合查询使用复合索引

```python
class StockAnalysisHistory(db.Model):
    __tablename__ = 'stock_analysis_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), index=True)
    ticker = db.Column(db.String(20), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (db.Index('idx_user_ticker', 'user_id', 'ticker'),)
```

### 4.4 外键约束

- 关联表必须使用 `db.ForeignKey` 定义外键
- 级联删除显式声明 `ondelete='CASCADE'`
- ORM 层用 `db.relationship()` 定义双向关系

---

## 5. 错误处理标准

### 5.1 异常捕获原则

**具体异常优先**，从具体到通用逐层捕获：

```python
try:
    result = analyze_stock(ticker)
    return jsonify({'success': True, 'data': result}), 200
except ValueError as e:
    logger.warning(f"参数错误: ticker={ticker}, error={e}")
    return jsonify({'error': str(e), 'code': 'INVALID_PARAMS'}), 400
except ConnectionError as e:
    logger.error(f"数据源连接失败: {e}")
    return jsonify({'error': '数据源暂不可用', 'code': 'DATA_UNAVAILABLE'}), 503
except Exception as e:
    logger.error(f"未预期错误: ticker={ticker}", exc_info=True)
    return jsonify({'error': '服务器内部错误', 'code': 'INTERNAL_ERROR'}), 500
```

### 5.2 日志级别区分

| 级别 | 场景 |
|------|------|
| `logger.warning()` | 参数不合法、降级处理、非致命异常 |
| `logger.error()` | 未捕获异常、外部服务故障、数据损坏 |

### 5.3 用户消息脱敏

- **禁止**将异常堆栈或数据库错误详情返回给用户
- 用户消息使用通用描述（"分析失败，请稍后重试"）
- 详细错误仅写入日志

---

## 6. 日志记录规范

### 6.1 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 详细调试信息（仅开发环境） | 函数入参、中间计算结果 |
| INFO | 常规业务事件 | 分析请求开始/完成 |
| WARNING | 非致命异常 | 数据缺失使用备用源 |
| ERROR | 需要关注的错误 | 外部 API 调用失败 |

### 6.2 日志格式

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

示例输出：
```
2026-02-08 14:30:22 - app.services.analysis_engine - INFO - 开始分析股票: AAPL, 风格: quality
2026-02-08 14:30:25 - app.services.analysis_engine - WARNING - 无法获取期权数据，使用备用数据源
```

### 6.3 日志内容要求

- 包含关键参数（`ticker`、`user_id`、`style`）
- 包含操作结果（成功/失败）
- 错误日志附带堆栈：`logger.error(msg, exc_info=True)`

### 6.4 敏感数据脱敏

以下数据**禁止**出现在日志中：用户密码、JWT Token 全文、支付卡号、完整 API Key。

如需记录，使用脱敏处理：
```python
logger.info(f"Token 验证: ...{token[-8:]}")
logger.info(f"API Key: {api_key[:4]}****")
```

---

## 7. 安全标准

### 7.1 认证机制

- Bearer JWT，由 Supabase Auth 签发
- 所有业务 API 必须经过 `@require_auth` 装饰器
- 唯一例外：`/health` 健康检查

```python
@bp.route('/api/stock/analyze', methods=['POST'])
@require_auth
def analyze_stock():
    user_id = g.user_id  # 从 JWT 解析
    ...
```

### 7.2 输入校验

所有参数在 Route 层校验后再传入 Service 层：

```python
ticker = request.json.get('ticker', '').strip().upper()
if not ticker or len(ticker) > 20:
    return jsonify({'error': '无效的股票代码', 'code': 'INVALID_TICKER'}), 400
```

### 7.3 SQL 注入防护

**强制使用** SQLAlchemy ORM 参数化查询，**禁止**拼接 SQL 字符串：

```python
# 正确
records = StockAnalysisHistory.query.filter_by(user_id=user_id).all()
# 禁止
db.execute(f"SELECT * FROM history WHERE user_id = '{user_id}'")
```

### 7.4 CORS 配置

当前状态：使用通配符 `*`（开发便利）。**生产环境待改进**为白名单模式：

```python
CORS(app, resources={r"/api/*": {
    "origins": ["https://alphag.app"],
    "methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})
```

### 7.5 密钥管理

- 所有密钥通过环境变量注入，禁止硬编码
- 本地使用 `.env` 文件（已加入 `.gitignore`）
- 生产环境通过部署平台 Secrets 管理

---

*最后更新: 2026-02-08*
*迁移自: docs/DESIGN_STANDARDS.md (Backend 部分)*
