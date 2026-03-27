# AlphaGBM API层 + OpenClaw Skill 开发计划

## 一、整体架构

```
用户从浏览器来 → React前端 → Flask后端（Supabase JWT认证）
用户从OpenClaw/MCP来 → Skill调API → Flask后端（API Key认证）
```

**核心原则：不建新系统，在现有Flask后端上加一层API Key认证。**

网站用户和API用户共享同一套账号、同一套额度、同一套分析引擎。两种认证方式，扣同一个账户的积分。

---

## 二、后端改动（4个文件）

### 2.1 新增 Model: ApiKey（models.py）

在现有 `models.py` 末尾新增：

```python
import secrets
import hashlib

class ApiKey(db.Model):
    """用户API密钥"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)  # SHA-256 hash
    key_prefix = db.Column(db.String(13), nullable=False)  # "agbm_" + 前8位hex，方便用户识别
    name = db.Column(db.String(100), nullable=False, default='Default')  # 用户给key起的名字
    is_active = db.Column(db.Boolean, default=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    user = db.relationship('User', backref=db.backref('api_keys', lazy=True))
    
    @staticmethod
    def generate_key():
        """生成 agbm_ 开头的API Key"""
        raw = secrets.token_hex(24)  # 48字符
        return f"agbm_{raw}"
    
    @staticmethod
    def hash_key(key):
        """SHA-256 hash"""
        return hashlib.sha256(key.encode()).hexdigest()
```

说明：
- Key格式: `agbm_` + 48位hex = 53字符总长
- 数据库只存hash，不存明文（安全）
- `key_prefix` 存前13位（`agbm_` + 8位hex），让用户在管理页面能识别是哪个key
- 用户可创建多个key（如"个人电脑""公司电脑"），最多5个

### 2.2 修改 auth.py — 双认证支持

修改现有的 `require_auth` 装饰器，通过token前缀自动区分认证方式：

```python
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing Authorization header'}), 401

        parts = auth_header.split(' ')
        if len(parts) < 2:
            return jsonify({'error': 'Invalid Authorization header format'}), 401

        scheme = parts[0].lower()
        token = parts[1]

        # ===== 方式1: API Key认证 =====
        # 格式: Authorization: Bearer agbm_xxxx
        if token.startswith('agbm_'):
            from ..models import db, ApiKey, User
            import hashlib
            
            key_hash = hashlib.sha256(token.encode()).hexdigest()
            api_key = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()
            
            if not api_key:
                return jsonify({'error': 'Invalid API key'}), 401
            
            # 更新最后使用时间
            api_key.last_used_at = datetime.utcnow()
            db.session.commit()
            
            # 设置用户上下文（和JWT认证完全一样的格式）
            user = User.query.get(api_key.user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            g.user_id = user.id
            g.user_email = user.email
            g.auth_method = 'api_key'  # 标记认证方式，方便日志区分
            
            return f(*args, **kwargs)

        # ===== 方式2: Supabase JWT认证（现有逻辑完全不变）=====
        if not supabase:
            return jsonify({'error': 'Supabase client not initialized'}), 500

        # ... 保留现有全部JWT认证代码，一字不改 ...
        
    return decorated
```

**关键点：**
- 通过token前缀 `agbm_` 自动区分认证方式，零冲突
- API Key用户复用完全相同的 `g.user_id`，所以下游的 `check_quota`、`UsageLog`、`DailyQueryCount` 等全部无需改动
- 加了 `g.auth_method = 'api_key'` 方便将来按来源统计

### 2.3 新增路由: api/api_key.py

```python
"""API Key管理路由"""

from flask import Blueprint, jsonify, request, g
from ..models import db, ApiKey
from ..utils.auth import require_auth

apikey_bp = Blueprint('apikey', __name__, url_prefix='/api/keys')

@apikey_bp.route('', methods=['GET'])
@require_auth
def list_keys():
    """列出用户所有API Key（只返回前缀，不返回完整key）"""
    keys = ApiKey.query.filter_by(user_id=g.user_id).all()
    return jsonify({
        'keys': [{
            'id': k.id,
            'name': k.name,
            'prefix': k.key_prefix,
            'is_active': k.is_active,
            'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
            'created_at': k.created_at.isoformat()
        } for k in keys]
    })

@apikey_bp.route('', methods=['POST'])
@require_auth
def create_key():
    """创建新API Key。注意：完整key只在创建时返回一次！"""
    data = request.get_json() or {}
    name = data.get('name', 'Default')
    
    # 限制每用户最多5个key
    existing_count = ApiKey.query.filter_by(user_id=g.user_id).count()
    if existing_count >= 5:
        return jsonify({'error': '最多创建5个API Key'}), 400
    
    # 生成key
    raw_key = ApiKey.generate_key()
    
    new_key = ApiKey(
        user_id=g.user_id,
        key_hash=ApiKey.hash_key(raw_key),
        key_prefix=raw_key[:13],  # "agbm_" + 前8位hex
        name=name
    )
    db.session.add(new_key)
    db.session.commit()
    
    return jsonify({
        'id': new_key.id,
        'key': raw_key,  # ⚠️ 唯一一次返回完整key
        'name': new_key.name,
        'prefix': new_key.key_prefix,
        'message': '请立即保存此API Key，关闭后将无法再次查看完整内容'
    }), 201

@apikey_bp.route('/<int:key_id>', methods=['DELETE'])
@require_auth
def delete_key(key_id):
    """删除（吊销）API Key"""
    key = ApiKey.query.filter_by(id=key_id, user_id=g.user_id).first()
    if not key:
        return jsonify({'error': 'Key not found'}), 404
    
    db.session.delete(key)
    db.session.commit()
    return jsonify({'message': 'API Key已删除'})

@apikey_bp.route('/<int:key_id>/toggle', methods=['POST'])
@require_auth
def toggle_key(key_id):
    """启用/停用API Key"""
    key = ApiKey.query.filter_by(id=key_id, user_id=g.user_id).first()
    if not key:
        return jsonify({'error': 'Key not found'}), 404
    
    key.is_active = not key.is_active
    db.session.commit()
    return jsonify({
        'id': key.id,
        'is_active': key.is_active,
        'message': f"API Key已{'启用' if key.is_active else '停用'}"
    })
```

### 2.4 注册Blueprint（__init__.py）

在 `create_app` 函数的 blueprint 注册区域加：

```python
from .api.api_key import apikey_bp
app.register_blueprint(apikey_bp)
```

---

## 三、限流中间件

### 新增 utils/rate_limiter.py

```python
"""API限流中间件"""

from flask import request, jsonify, g
from functools import wraps
import time
from collections import defaultdict

# 简单内存限流（生产环境建议用Redis）
rate_limit_store = defaultdict(list)

def rate_limit(max_requests=60, window_seconds=60):
    """限流装饰器 - 只对API Key用户生效"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 只对API Key用户限流（网站用户走前端限制）
            if getattr(g, 'auth_method', None) != 'api_key':
                return f(*args, **kwargs)
            
            user_id = g.user_id
            now = time.time()
            
            # 清理过期记录
            rate_limit_store[user_id] = [
                t for t in rate_limit_store[user_id] 
                if t > now - window_seconds
            ]
            
            if len(rate_limit_store[user_id]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window_seconds,
                    'limit': max_requests
                }), 429
            
            rate_limit_store[user_id].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator
```

**使用方式** — 在需要限流的endpoint上加装饰器，放在 `@require_auth` 之后、`@check_quota` 之前：

```python
@options_bp.route('/chain-async', methods=['POST'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)  # 新增
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def analyze_options_chain_async():
    ...
```

---

## 四、前端改动

### 4.1 新增页面: pages/ApiKeys.tsx

**页面结构（从上到下）：**

1. **标题区**
   - 标题：🔑 API Key 管理
   - 说明文字：通过API Key，您可以在OpenClaw、Claude Desktop等AI工具中使用AlphaGBM的分析能力
   - 按钮：[+ 创建新Key]（右对齐，teal filled）

2. **Key列表**（卡片样式）
   - 每个Key一个卡片
   - 显示：名称、Key前缀(agbm_3f8a2b1c••••)、创建日期、最后使用时间、状态（绿点启用/灰点停用）
   - 操作：[停用/启用] [删除]（删除需二次确认）

3. **创建弹窗（Modal）**
   - 输入态：Key名称输入框 + [取消] [创建]
   - 成功态：⚠️警告banner + 完整Key展示（monospace）+ 复制按钮 + [完成]

4. **快速开始指南**（底部，可折叠）
   - 左栏 OpenClaw用户：安装命令 + 设环境变量 + 使用示例
   - 右栏 API开发者：curl命令示例 + API文档链接

5. **底部统计条**
   - 本月API调用: 47次 | 剩余额度: 953次 | 当前套餐: Plus

**设计参考：** OpenAI platform.openai.com 的 API Keys 页面
**配色：** 现有主题色 #0D9B97，背景 #0f0f23，卡片 #1a1a2e

### 4.2 修改: Profile.tsx

在个人中心页面加一个入口卡片：

```tsx
// 在现有卡片下方新增
<Card>
  <CardTitle>🔑 API访问</CardTitle>
  <p>已创建 {keyCount} 个API Key</p>
  <p>本月API调用: {apiCallCount} 次</p>
  <Link to="/api-keys">管理API Key →</Link>
</Card>
```

### 4.3 路由（App.tsx）

```tsx
<Route path="/api-keys" element={<ApiKeys />} />
```

---

## 五、OpenClaw Skill

创建 `alphagbm-options/` 文件夹，包含两个文件：

### 5.1 SKILL.md

```markdown
# AlphaGBM Options — AI期权分析

## 配置
用户需要在 alphagbm.com 注册并获取API Key。
API Key设为环境变量: ALPHAGBM_API_KEY

## 能力
- 股票分析（输入ticker，获取AI分析报告）
- 期权链分析（输入ticker+到期日，获取评分和策略推荐）
- 期权深度分析（输入具体合约，获取Greeks/VRP/风险分析）

## API调用方式

### 股票分析
POST https://alphagbm.com/api/stock/analyze-async
Headers: Authorization: Bearer $ALPHAGBM_API_KEY
Content-Type: application/json
Body: {"ticker": "TSLA", "style": "balanced"}

### 期权链分析
POST https://alphagbm.com/api/options/chain-async
Headers: Authorization: Bearer $ALPHAGBM_API_KEY
Content-Type: application/json
Body: {"symbol": "TSLA", "expiry_date": "2026-04-17"}

### 深度期权分析
POST https://alphagbm.com/api/options/enhanced-async
Headers: Authorization: Bearer $ALPHAGBM_API_KEY
Content-Type: application/json
Body: {"symbol": "TSLA", "option_identifier": "TSLA260417C00250000"}

### 查询任务结果（异步任务需轮询）
GET https://alphagbm.com/api/tasks/{task_id}
Headers: Authorization: Bearer $ALPHAGBM_API_KEY

### 额度查询
GET https://alphagbm.com/api/user/quota
Headers: Authorization: Bearer $ALPHAGBM_API_KEY

## 使用规则
- 所有API调用消耗用户在alphagbm.com的额度
- 免费用户：每日2次股票分析 + 1次期权分析
- 付费用户：按套餐额度（Plus 1000次/月，Pro 5000次/月）
- 额度不足时API返回 {"error": "额度不足", "upgrade_url": "https://alphagbm.com/pricing"}
- 遇到额度不足，告知用户去 alphagbm.com/pricing 升级

## 输出格式
将API返回的JSON格式化为易读的文字报告：
- 股票分析：评级(买入/增持/中性/观望) + 目标价 + 风险评分 + AI总结
- 期权分析：推荐策略 + 评分 + Greeks + VRP分析 + 风险提示
```

### 5.2 package.json

```json
{
  "name": "alphagbm-options",
  "version": "1.0.0",
  "description": "AI-powered stock & options analysis via AlphaGBM.com API",
  "keywords": ["options", "stocks", "finance", "trading", "期权", "期权分析"],
  "author": "AlphaGBM",
  "license": "MIT"
}
```

---

## 六、数据库迁移

只需要加一张表。如果用 SQLAlchemy 的 `db.create_all()`，Flask启动时会自动创建。

手动SQL（如果需要）：

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES "user"(id),
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    key_prefix VARCHAR(13) NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT 'Default',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
```

---

## 七、开发优先级和工期

### P0 核心功能（1-2天）
1. ✅ models.py 加 ApiKey 模型
2. ✅ auth.py 改双认证（agbm_ 前缀判断）
3. ✅ api_key.py 新增 CRUD 路由
4. ✅ __init__.py 注册 blueprint

### P1 前端（1天）
5. ✅ ApiKeys.tsx 页面
6. ✅ Profile.tsx 加入口卡片
7. ✅ App.tsx 加路由

### P2 分发（0.5天）
8. ✅ SKILL.md — 后端 `/api/docs/` 提供纯文本供 AI Agent 读取
9. ✅ OpenAPI spec — `/api/docs/openapi.yaml` + `/api/docs/openapi.json`
10. ⬜ 发布到 ClawHub（基础设施就绪，尚未作为独立 skill 发布）

### P3 完善（1天）
11. ✅ API文档 — 方案调整：不再用前端 marked.js 渲染，改为后端 `/api/docs/` 直接提供（docs blueprint）
12. ✅ 限流中间件 — `utils/rate_limiter.py` 已实现（内存滑动窗口，60次/分钟），⚠️ 但尚未挂载到任何路由
13. ⬜ API调用统计（在Profile里显示"本月API调用次数"）

**总计约 3-4 天**

---

## 八、后续升级路径

### Phase 2: MCP Server（Phase 1完成后2周）
把API封装成MCP Server，任何支持MCP的AI工具（Claude Desktop、Cursor、Windsurf）都能直接调用：
```json
{
  "mcpServers": {
    "alphagbm": {
      "command": "npx",
      "args": ["alphagbm-mcp-server"],
      "env": {"ALPHAGBM_API_KEY": "agbm_xxx"}
    }
  }
}
```

### Phase 3: Webhook + 持仓监控
用户授权券商API → AlphaGBM监控持仓 → Greeks异常/到期提醒推送。从"查询工具"升级为"监控服务"，从按次收费变按月订阅。

### Phase 4: 策略社区
用户发布期权策略 + AlphaGBM回测验证 → 其他用户订阅跟单。从工具平台变社区平台。

---

## 九、给Cursor的任务描述

### 任务1: 后端API Key系统

```
在现有Flask后端上添加API Key认证系统：

1. models.py 新增 ApiKey 模型
   - 字段：id(自增), user_id(FK→user), key_hash(SHA-256,唯一), key_prefix(前13位明文), name(用户命名), is_active(布尔), last_used_at, created_at
   - 静态方法：generate_key()生成agbm_开头key, hash_key()做SHA-256
   - 关联User表

2. auth.py 修改 require_auth 装饰器，支持双认证：
   - 读取Authorization header的token
   - 如果token以 agbm_ 开头 → API Key认证：hash token → 查api_keys表 → 验证is_active → 设置g.user_id和g.auth_method='api_key'
   - 否则 → 走现有Supabase JWT认证（所有代码不变）
   - 关键：API Key用户设置的g.user_id和JWT用户完全一样，下游check_quota/UsageLog零改动

3. 新增 api/api_key.py：
   - Blueprint: apikey_bp, prefix=/api/keys
   - GET /api/keys — 列出用户所有key（只返回前缀不返回完整key）
   - POST /api/keys — 创建新key（完整key只返回一次），每用户最多5个
   - DELETE /api/keys/<id> — 删除key（验证是当前用户的）
   - POST /api/keys/<id>/toggle — 启用/停用

4. __init__.py 注册 apikey_bp

5. 新增 utils/rate_limiter.py：
   - rate_limit装饰器，只对API Key用户生效（g.auth_method=='api_key'）
   - 默认60次/分钟
   - 超限返回429 + retry_after
   - 内存实现（defaultdict + 时间窗口）

现有文件位置：
- models.py: backend/app/models.py
- auth.py: backend/app/utils/auth.py
- __init__.py: backend/app/__init__.py
- decorators.py: backend/app/utils/decorators.py（check_quota在这里，不用改）
```

### 任务2: 前端API Key管理

```
新增API Key管理页面，参考OpenAI platform.openai.com API Keys页面风格。

1. 新建 pages/ApiKeys.tsx
   页面结构（从上到下）：
   - 标题区：🔑 API Key 管理 + 说明文字 + [+ 创建新Key]按钮
   - Key列表：卡片样式，每个key显示名称/前缀/状态/创建时间/最后使用时间，操作按钮[停用][删除]
   - 创建弹窗(Modal)：两个状态——输入态(名称输入框)和成功态(⚠️警告+完整key+复制按钮)
   - 快速开始指南：两列布局，左栏OpenClaw用户(安装+配置+使用)，右栏API开发者(curl示例)
   - 底部统计：本月API调用次数 / 剩余额度 / 当前套餐

2. 修改 Profile.tsx
   - 加一个"🔑 API访问"卡片，显示key数量和调用次数，链接到/api-keys

3. App.tsx 加路由 /api-keys → ApiKeys组件

4. API调用：
   - GET /api/keys — 获取列表
   - POST /api/keys — 创建（body: {name: "xxx"}）
   - DELETE /api/keys/:id — 删除
   - POST /api/keys/:id/toggle — 启停

配色：主题色 #0D9B97，背景 #0f0f23，卡片 #1a1a2e
字体：Inter + Noto Sans SC（现有）
组件：复用现有ui组件库
```
