# AlphaG 期权分析模块

## 📊 模块简介

这是 AlphaG 智能投研系统的**期权分析模块**，基于 `G = B + M` 模型，为股票期权交易提供智能策略建议。

## 🎯 核心功能

### 1. AlphaG 模型分析
- **G (Gain)**: 综合收益分 (0-100)
- **B (Basics)**: 基本面锚点 (0-10)
  - 营收增长率
  - 利润率
  - PEG估值
- **M (Momentum)**: 市场动量 (0-10)
  - 技术趋势 (MA50/MA200)
  - 乖离率
  - 超买超卖判断

### 2. 智能期权策略

| AlphaG 诊断 | 对应策略 | 说明 |
|-------------|---------|------|
| B优 + M低 (黄金坑) | 🛡️ Sell Put (安全建仓) | 公司好但被错杀，在支撑位卖Put |
| B优 + M高 (主升浪) | 📈 Long Call / Bull Spread | 基本面好且动量爆发 |
| 持仓中 + M过热 | 📤 Covered Call | 止盈增强 |
| B差 (垃圾股) | ⛔ 禁止操作 | 基本面恶化，严禁卖Put |

### 3. 关键指标
- **年化收益 (AR)**: 期权策略的年化回报率
- **安全边际**: 当前价格与行权价的差距
- **支撑位 (MA200)**: 基于200日均线的关键支撑
- **Delta**: 期权希腊值

## 🚀 快速开始

### 1. 安装依赖

```bash
cd options_module
pip install -r requirements.txt
```

### 2. 配置 API Key

创建 `.env` 文件：

```env
POLYGON_API_KEY=your_polygon_api_key_here
```

> 📝 获取 Polygon API Key: https://polygon.io (免费版可用)

### 3. 启动服务

```bash
python main.py
```

服务将在 http://127.0.0.1:8000 启动

### 4. 访问界面

打开浏览器访问: http://127.0.0.1:8000

## 📐 设计系统

本模块完全遵循 AlphaP 设计系统规范：

- **品牌色**: `#0D9B97` (青色)
- **基本面色**: `#10B981` (绿色)
- **市场情绪色**: `#F59E0B` (橙黄色)
- **看涨色**: `#10B981` (绿色)
- **看跌色**: `#EF4444` (红色)
- **深色主题**: 金融终端风格

## 🔗 与主系统集成

### 方式1: 独立运行 (推荐开发阶段)

```bash
# 终端1: 主系统
cd /path/to/AlphaG股票分析系统
python app.py  # 运行在 5002 端口

# 终端2: 期权模块
cd /path/to/AlphaG股票分析系统/options_module
python main.py  # 运行在 8000 端口
```

### 方式2: 导航集成

在主系统 `templates/base.html` 的导航栏中添加链接：

```html
<li class="nav-item">
    <a class="nav-link" href="http://localhost:8000" target="_blank">
        <i class="bi bi-graph-up"></i> 期权分析
    </a>
</li>
```

## 📊 API 文档

### GET `/api/analyze/{symbol}`

分析指定股票的期权策略

**参数**:
- `symbol` (path): 股票代码，如 `NVDA`, `TSLA`

**响应**:
```json
{
  "alpha_p": {
    "symbol": "NVDA",
    "p_score": 72.5,
    "f_score": 8.0,
    "s_score": 6.5,
    "risk_level": "Low",
    "target_price": 150.0,
    "recommendation": "Buy",
    "risk_flags": [],
    "support_level": 120.5
  },
  "price": 135.50,
  "options": [
    {
      "expiry": "2024-12-20",
      "strike": 130.0,
      "type": "put",
      "bid": 2.50,
      "ask": 2.70,
      "delta": -0.35,
      "annualized_return": 18.5,
      "premium_income": 260.0,
      "price_diff_percent": 4.07,
      "p_strategy_tag": "🛡️ P-Model: 安全建仓",
      "is_recommended": true
    }
  ]
}
```

## 🔧 技术架构

- **后端**: FastAPI + Python 3.8+
- **数据源**: 
  - yfinance (股票基本面)
  - Polygon.io API (期权链数据)
- **前端**: 
  - AG Grid Community (表格)
  - Bootstrap 5 (UI组件)
  - AlphaP Design System (自定义样式)

## ⚠️ 注意事项

1. **API限制**: Polygon 免费版有调用次数限制，建议适度使用
2. **数据延迟**: 免费API可能有15分钟延迟
3. **风险提示**: 本系统仅供研究学习，不构成投资建议
4. **独立运行**: 本模块与主系统独立，互不影响

## 📝 更新日志

### v1.0.0 (2025-12-26)
- ✅ 初始版本发布
- ✅ 实现 AlphaG (G=B+M) 核心模型
- ✅ 集成 Polygon 期权数据
- ✅ 匹配 AlphaP 设计系统
- ✅ 智能策略推荐

## 🤝 支持

如有问题，请联系开发团队或提交 Issue。

---

**© 2025 Alpha GBM. 基于 G=B+M 投资框架**

