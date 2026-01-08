# 智能体服务集成指南

## 🔗 与主系统联动

### 1. 主系统调用智能体服务

在主系统的 `app.py` 中添加代理路由：

```python
@app.route('/api/agent/chat', methods=['POST'])
@jwt_required()
def agent_chat_proxy():
    """代理智能体服务的聊天接口"""
    import requests
    
    user_info = get_user_info_from_token()
    if not user_info or 'user_id' not in user_info:
        return jsonify({'error': '请先登录'}), 401
    
    # 获取用户的JWT token（用于传递给智能体服务）
    token = request.headers.get('Authorization', '')
    
    # 转发请求到智能体服务
    agent_url = os.getenv('AGENT_SERVICE_URL', 'http://localhost:8001/api/v1/chat')
    
    try:
        response = requests.post(
            agent_url,
            json=request.json,
            headers={'Authorization': token},
            stream=True,
            timeout=30
        )
        
        # 流式返回
        def generate():
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({'error': f'智能体服务连接失败: {str(e)}'}), 500
```

### 2. 前端集成

在主系统的前端页面中：

```javascript
// static/agent.js
async function chatWithAgent(message) {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch('/api/agent/chat', {
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
        
        if (!response.ok) {
            if (response.status === 402) {
                // 额度不足，显示付费提示
                showPaywall();
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const chatContainer = document.getElementById('chat-container');
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.content) {
                            // 追加内容到聊天界面
                            appendMessage('assistant', data.content);
                        } else if (data.done) {
                            // 对话结束
                            console.log('对话完成');
                        } else if (data.error) {
                            // 错误处理
                            showError(data.error);
                        }
                    } catch (e) {
                        console.error('解析SSE数据失败:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('智能体请求失败:', error);
        showError('连接智能体服务失败，请稍后重试');
    }
}

function appendMessage(role, content) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.textContent = content;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
```

### 3. 环境变量配置

在主系统的 `.env` 文件中添加：

```env
# 智能体服务配置
AGENT_SERVICE_URL=http://localhost:8001
```

## 🔄 数据同步

### 用户权限同步

智能体服务使用Supabase进行鉴权，主系统需要同步用户权限：

```python
# 在主系统的用户注册/订阅更新时，同步到Supabase
def sync_user_to_supabase(user_id, plan_tier):
    """同步用户权限到Supabase"""
    from supabase import create_client
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )
    
    # 更新profiles表
    supabase.table("profiles").upsert({
        "id": user_id,
        "agent_tier": "pro" if plan_tier in ["pro", "plus"] else "free",
        "agent_daily_usage": 0,
        "agent_last_reset": datetime.now().isoformat()
    }).execute()
```

## 🚀 部署方案

### 方案1: 同服务器不同端口（开发环境）

- 主服务: `http://localhost:5002`
- 智能体服务: `http://localhost:8001`

### 方案2: 独立服务器（生产环境）

- 主服务: `https://api.alphagbm.com`
- 智能体服务: `https://agent.alphagbm.com`

使用Nginx反向代理：

```nginx
# 主服务
server {
    listen 80;
    server_name api.alphagbm.com;
    location / {
        proxy_pass http://localhost:5002;
    }
}

# 智能体服务
server {
    listen 80;
    server_name agent.alphagbm.com;
    location / {
        proxy_pass http://localhost:8001;
    }
}
```

## 📊 监控与日志

### 日志配置

在 `main.py` 中添加日志：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent_service.log'),
        logging.StreamHandler()
    ]
)
```

### 健康检查

主系统可以定期检查智能体服务状态：

```python
@app.route('/api/agent/health', methods=['GET'])
def check_agent_health():
    """检查智能体服务健康状态"""
    import requests
    
    agent_url = os.getenv('AGENT_SERVICE_URL', 'http://localhost:8001')
    
    try:
        response = requests.get(f'{agent_url}/api/v1/health', timeout=5)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503
```

## 🔐 安全注意事项

1. **Token传递**: 确保JWT token安全传递，不要泄露
2. **CORS配置**: 生产环境限制CORS来源
3. **速率限制**: 建议添加API速率限制
4. **错误处理**: 不要暴露内部错误信息给用户

## 🧪 测试

### 测试智能体服务

```bash
# 启动服务
cd alpha_agent_service
python main.py

# 测试健康检查
curl http://localhost:8001/api/v1/health

# 测试对话（需要有效token）
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "分析AAPL"}]}'
```
