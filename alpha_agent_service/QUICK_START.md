# 智能体服务快速启动指南

## 🚀 5分钟快速启动

### 1. 安装依赖

```bash
cd alpha_agent_service
pip install -r requirements.txt
playwright install  # Crawl4AI需要
```

### 2. 配置环境变量

```bash
# 复制模板
cp env_template.txt .env

# 编辑 .env 文件，填写必要的密钥
# - OPENAI_API_KEY (必需)
# - SUPABASE_URL (必需)
# - SUPABASE_SERVICE_KEY (必需)
# - TUSHARE_TOKEN (A股数据需要)
```

### 3. 启动服务

```bash
# 方式1: 使用启动脚本
./start.sh

# 方式2: 直接运行
python main.py
```

服务将在 `http://localhost:8001` 启动。

## 📋 必需配置

### 最小配置（.env）

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### 完整配置（.env）

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
TUSHARE_TOKEN=你的TushareToken
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
AGENT_SERVICE_PORT=8001
CORS_ORIGINS=http://localhost:5002,http://localhost:3000
FREE_USER_DAILY_QUOTA=5
```

## 🧪 测试服务

### 1. 健康检查

```bash
curl http://localhost:8001/api/v1/health
```

### 2. 测试对话（需要有效Token）

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "分析一下AAPL"}
    ]
  }'
```

## 🔗 与主系统集成

在主系统的 `app.py` 中添加代理路由（参考 `INTEGRATION_GUIDE.md`）。

## ⚠️ 常见问题

### 1. 模块未找到

```bash
# 确保在虚拟环境中
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Playwright错误

```bash
playwright install chromium
```

### 3. Supabase连接失败

- 检查URL和Service Key是否正确
- 确认网络连接正常
- 检查Supabase项目是否激活

### 4. OpenAI API错误

- 检查API Key是否有效
- 确认账户有足够余额
- 检查速率限制

## 📚 下一步

- 查看 [README.md](./README.md) 了解完整功能
- 查看 [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) 了解如何与主系统集成
