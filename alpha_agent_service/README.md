# AlphaGBM 智能体服务

## 📦 模块概述

独立的AI智能体服务，基于 **G=B+M (价格 = 基本面 + 情绪)** 模型提供专业的投资分析。与主系统（`app.py`）完全分离，运行在独立端口（8001），通过API与主系统联动。

## 🎯 核心特性

### 1. 全能型数据获取
- **股市工具**: 支持A股（Tushare）、美股/港股（YFinance）
- **爬虫工具**: 使用Crawl4AI深度阅读财经新闻、财报
- **币圈工具**: 查询链上代币数据（DexScreener）

### 2. G=B+M 模型注入
- **G (价格位置)**: 分析当前价格与52周高低的关系
- **B (基本面)**: 验证营收增长、ROE、利润率等
- **M (情绪/叙事)**: 结合PE、PEG、新闻热度判断情绪

### 3. 独立收费与鉴权
- 使用Supabase进行用户鉴权
- 免费用户每日5次限制
- Pro/Plus用户无限制

### 4. 流式对话
- 支持实时流式输出
- 工具调用状态通知
- 错误处理机制

## 🏗️ 项目结构

```
alpha_agent_service/
├── .env                  # 环境变量配置
├── requirements.txt      # 依赖包
├── main.py               # 启动入口
└── app/
    ├── __init__.py
    ├── config.py         # 配置管理
    ├── core/             # 工具层
    │   ├── tools_stock.py    # 股市工具
    │   ├── tools_crypto.py   # 币圈工具
    │   └── tools_web.py      # 爬虫工具
    ├── agent/            # 智能体层
    │   ├── prompts.py    # G=B+M提示词
    │   ├── state.py      # LangGraph状态
    │   └── graph.py      # 工作流图
    └── api/              # API层
        ├── deps.py       # 鉴权依赖
        └── routes.py     # 路由定义
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd alpha_agent_service
pip install -r requirements.txt

# 安装Playwright（Crawl4AI需要）
playwright install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写：

```env
OPENAI_API_KEY=sk-...
TUSHARE_TOKEN=你的TushareToken
SUPABASE_URL=你的SupabaseURL
SUPABASE_SERVICE_KEY=你的ServiceRoleKey
```

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8001` 启动。

## 📡 API接口

### 1. 流式对话

```http
POST /api/v1/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "分析一下AAPL"}
  ]
}
```

**响应**: `text/event-stream` 格式的流式数据

### 2. 健康检查

```http
GET /api/v1/health
```

### 3. 使用指南

```http
GET /api/v1/guide
```

## 🔗 与主系统联动

### 前端集成示例

在主系统的前端页面中：

```javascript
// 调用智能体服务
async function chatWithAgent(message) {
    const token = localStorage.getItem('token');
    
    const response = await fetch('http://localhost:8001/api/v1/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            messages: [
                { role: 'user', content: message }
            ]
        })
    });
    
    // 处理流式响应
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        // 解析SSE格式数据
        const lines = chunk.split('\n');
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                if (data.content) {
                    // 显示内容
                    console.log(data.content);
                }
            }
        }
    }
}
```

## 🛠️ 工具说明

### 股市工具 (`tools_stock.py`)

- `get_stock_metrics(ticker)`: 获取G=B+M指标
- `get_stock_news(ticker, limit)`: 获取股票新闻

### 爬虫工具 (`tools_web.py`)

- `read_webpage_content(url)`: 深度阅读网页内容
- `search_web_content(query)`: 网络搜索（需配置）

### 币圈工具 (`tools_crypto.py`)

- `check_chain_token(token_address, chain)`: 查询链上代币数据
- `get_crypto_news(limit)`: 获取加密货币新闻（需配置）

## 🔒 权限管理

### 用户层级

- **Free**: 每日5次调用限制
- **Plus**: 无限制
- **Pro**: 无限制

### Supabase表结构

需要在Supabase的`profiles`表中添加字段：

```sql
ALTER TABLE profiles ADD COLUMN agent_tier VARCHAR(50) DEFAULT 'free';
ALTER TABLE profiles ADD COLUMN agent_daily_usage INTEGER DEFAULT 0;
ALTER TABLE profiles ADD COLUMN agent_last_reset TIMESTAMP;
```

## 📝 注意事项

1. **独立运行**: 服务运行在8001端口，与主服务(5002)完全分离
2. **环境变量**: 必须配置OpenAI、Supabase和Tushare密钥
3. **Playwright**: Crawl4AI需要安装Playwright浏览器
4. **Token消耗**: 每次对话会消耗OpenAI Token，注意成本控制
5. **并发限制**: 建议配置OpenAI的并发限制

## 🐛 故障排查

### 1. 服务无法启动

- 检查环境变量是否配置完整
- 检查端口8001是否被占用
- 查看错误日志

### 2. 工具调用失败

- **Tushare**: 检查Token是否有效
- **Crawl4AI**: 确认Playwright已安装
- **DexScreener**: 检查网络连接

### 3. 鉴权失败

- 检查Supabase配置
- 确认Token格式正确（Bearer token）
- 检查用户权限表结构

## 📚 相关文档

- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [Crawl4AI文档](https://github.com/unclecode/crawl4ai)
- [Supabase文档](https://supabase.com/docs)
