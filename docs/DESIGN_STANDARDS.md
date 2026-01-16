# AlphaG 设计标准文档

本文档定义了 AlphaG 系统的设计标准、编码规范和最佳实践。

## 📋 目录

- [架构设计原则](#架构设计原则)
- [代码组织规范](#代码组织规范)
- [API 设计标准](#api-设计标准)
- [数据库设计规范](#数据库设计规范)
- [前端设计规范](#前端设计规范)
- [错误处理标准](#错误处理标准)
- [日志记录规范](#日志记录规范)
- [安全标准](#安全标准)

## 🏗️ 架构设计原则

### 1. 分层架构

系统采用清晰的分层架构：

```
┌─────────────────────────────────┐
│      Presentation Layer          │  React Frontend
│      (UI Components)             │
├─────────────────────────────────┤
│      API Layer                   │  Flask Blueprints
│      (REST Endpoints)            │
├─────────────────────────────────┤
│      Service Layer               │  Business Logic
│      (Analysis Engines)          │
├─────────────────────────────────┤
│      Data Layer                  │  Models & Database
│      (SQLAlchemy Models)         │
└─────────────────────────────────┘
```

### 2. 关注点分离

- **API 层**：只负责请求处理、参数验证、响应格式化
- **Service 层**：包含所有业务逻辑和算法
- **Model 层**：只负责数据定义和数据库操作
- **Utils 层**：提供可复用的工具函数

### 3. 依赖注入

使用 Flask 应用上下文进行依赖注入，避免全局变量：

```python
# ✅ 正确
def create_app():
    app = Flask(__name__)
    db.init_app(app)
    return app

# ❌ 错误
db = SQLAlchemy()  # 全局变量
```

## 📁 代码组织规范

### 后端目录结构

```
backend/app/
├── api/              # API 路由（Blueprint）
│   ├── auth.py
│   ├── stock.py
│   └── options.py
├── services/         # 业务逻辑层
│   ├── analysis_engine.py
│   ├── options_service.py
│   └── payment_service.py
├── analysis/         # 分析算法模块
│   ├── stock_analysis/
│   └── options_analysis/
├── models.py         # 数据模型
├── config.py         # 配置类
└── constants.py      # 常量定义
```

### 命名规范

#### Python

- **类名**：PascalCase (`StockAnalysisEngine`)
- **函数/变量**：snake_case (`calculate_risk_score`)
- **常量**：UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)
- **私有方法**：前缀单下划线 (`_internal_method`)

#### TypeScript

- **类名**：PascalCase (`StockAnalysisComponent`)
- **函数/变量**：camelCase (`calculateRiskScore`)
- **常量**：UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)
- **类型/接口**：PascalCase (`StockAnalysisResult`)

### 文件组织

- 每个模块一个文件
- 相关功能放在同一目录
- 避免循环依赖
- 保持文件大小 < 500 行（如可能）

## 🔌 API 设计标准

### RESTful 规范

- **GET**：获取资源
- **POST**：创建资源或执行操作
- **PUT**：更新资源（完整更新）
- **PATCH**：部分更新资源
- **DELETE**：删除资源

### URL 设计

```
/api/{resource}/{id}/{sub-resource}
```

示例：
- `GET /api/stock/history` - 获取分析历史列表
- `GET /api/stock/history/123` - 获取特定分析记录
- `POST /api/options/analyze` - 执行期权分析

### 请求格式

```json
{
  "ticker": "AAPL",
  "style": "quality",
  "options": {}
}
```

### 响应格式

**成功响应**：
```json
{
  "success": true,
  "data": { ... },
  "remaining_credits": 150
}
```

**错误响应**：
```json
{
  "success": false,
  "error": "错误描述",
  "code": "ERROR_CODE",
  "remaining_credits": 0
}
```

### HTTP 状态码

- `200`：成功
- `201`：创建成功
- `400`：请求参数错误
- `401`：未授权
- `402`：积分不足
- `403`：禁止访问
- `404`：资源不存在
- `500`：服务器错误

### 认证

使用 Bearer Token 认证：

```
Authorization: Bearer <jwt_token>
```

## 🗄️ 数据库设计规范

### 表命名

- 使用复数形式：`users`, `stock_analysis_history`
- 使用下划线分隔：`stock_analysis_history`（不是 `stockAnalysisHistory`）
- 关联表：`user_subscriptions`

### 字段命名

- 主键：`id` (INTEGER PRIMARY KEY)
- 外键：`user_id`, `stock_id`
- 时间戳：`created_at`, `updated_at`
- 布尔值：`is_active`, `has_permission`

### 索引

- 主键自动索引
- 外键字段创建索引
- 常用查询字段创建索引
- 复合索引用于多字段查询

```python
# 示例
class StockAnalysisHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), index=True)
    ticker = db.Column(db.String(20), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 复合索引
    __table_args__ = (
        db.Index('idx_user_ticker', 'user_id', 'ticker'),
    )
```

## 🎨 前端设计规范

### 组件组织

```
src/
├── components/
│   ├── ui/              # 基础 UI 组件（Button, Input 等）
│   ├── layouts/         # 布局组件（Header, Footer）
│   └── features/        # 功能组件（StockAnalysis, OptionsChain）
├── pages/               # 页面组件
├── hooks/               # 自定义 Hooks
├── lib/                 # 工具库
└── types/               # TypeScript 类型定义
```

### 组件命名

- 组件文件：PascalCase (`StockAnalysis.tsx`)
- Hook 文件：camelCase with `use` prefix (`useStockAnalysis.ts`)
- 工具文件：camelCase (`api.ts`, `utils.ts`)

### 状态管理

- 使用 React Hooks (`useState`, `useEffect`)
- 全局状态使用 Context API
- 复杂状态考虑使用 Zustand 或 Redux

### 样式规范

- 使用 Tailwind CSS 工具类
- 自定义样式放在 `index.css`
- 遵循集中式样式系统（见记忆）

## ⚠️ 错误处理标准

### 后端错误处理

```python
# ✅ 正确
try:
    result = analyze_stock(ticker)
    return jsonify({'success': True, 'data': result})
except ValueError as e:
    logger.warning(f"参数错误: {e}")
    return jsonify({'success': False, 'error': str(e)}), 400
except Exception as e:
    logger.error(f"分析失败: {e}", exc_info=True)
    return jsonify({'success': False, 'error': '分析失败'}), 500

# ❌ 错误
result = analyze_stock(ticker)  # 没有错误处理
return jsonify(result)
```

### 前端错误处理

```typescript
// ✅ 正确
try {
  const response = await api.post('/api/stock/analyze', data);
  setResult(response.data);
} catch (error) {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 402) {
      setError('积分不足，请充值');
    } else {
      setError(error.response?.data?.error || '分析失败');
    }
  }
}
```

## 📝 日志记录规范

### 日志级别

- **DEBUG**：详细调试信息
- **INFO**：一般信息（请求处理、任务完成）
- **WARNING**：警告信息（参数异常、降级处理）
- **ERROR**：错误信息（异常捕获）
- **CRITICAL**：严重错误（系统崩溃风险）

### 日志格式

```python
logger.info(f"开始分析股票: {ticker}, 风格: {style}")
logger.warning(f"无法获取期权数据，使用备用数据源")
logger.error(f"分析失败: {e}", exc_info=True)
```

### 日志内容

- 包含关键参数（ticker, user_id）
- 包含操作结果（成功/失败）
- 错误日志包含堆栈信息（`exc_info=True`）

## 🔒 安全标准

### 认证与授权

- 所有 API 端点（除 `/health`）需要认证
- 使用 JWT Token 验证
- 验证用户权限和积分

### 输入验证

```python
# ✅ 正确
ticker = request.json.get('ticker', '').strip().upper()
if not ticker or len(ticker) > 20:
    return jsonify({'error': '无效的股票代码'}), 400

# ❌ 错误
ticker = request.json['ticker']  # 没有验证
```

### 数据保护

- 敏感信息不记录到日志
- 使用环境变量存储密钥
- SQL 查询使用参数化（防止 SQL 注入）
- 限制 API 调用频率

### CORS 配置

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "https://yourdomain.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

## 📊 性能标准

### 响应时间目标

- API 响应时间 < 2 秒（正常情况）
- 异步任务响应 < 100ms（任务创建）
- 前端页面加载 < 3 秒

### 数据库优化

- 使用连接池
- 添加适当的索引
- 避免 N+1 查询
- 使用分页（避免一次性加载大量数据）

### 缓存策略

- 静态数据缓存（到期日列表）
- 用户会话缓存
- API 响应缓存（如适用）

## 🧪 测试标准

### 单元测试

- 每个 Service 函数至少一个测试
- 测试覆盖率 > 70%
- 使用 Mock 隔离外部依赖

### 集成测试

- API 端点集成测试
- 数据库操作测试
- 第三方服务集成测试

## 📚 文档标准

### 代码注释

```python
def calculate_risk_score(data: dict, style: str) -> float:
    """
    计算股票风险评分
    
    参数:
        data: 市场数据字典，包含 price, pe, growth 等
        style: 投资风格 ('quality', 'value', 'growth', 'momentum')
    
    返回:
        风险评分 (0-10)，分数越高风险越大
    
    异常:
        ValueError: 当数据不完整时抛出
    """
    pass
```

### API 文档

- 使用 OpenAPI/Swagger 规范
- 提供请求/响应示例
- 说明错误码和错误信息

---

**最后更新**: 2026-01-16
