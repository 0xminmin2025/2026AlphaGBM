# AlphaGBM 期权分析模块

## 📊 模块简介

这是 AlphaGBM 智能投研系统的**期权分析模块**，基于 `G = B + M` 模型，为股票期权交易提供智能策略建议。

## 🎯 核心功能

### 1. AlphaGBM 模型分析
- **G (Gain)**: 综合收益分 (0-100)
- **B (Basics)**: 基本面锚点 (0-10)
  - 营收增长率
  - 利润率
  - PEG估值
- **M (Momentum)**: 市场动量 (0-10)
  - 技术趋势 (MA50/MA200)
  - 乖离率
  - 超买超卖判断

### 2. 智能期权策略（全新优化版本）

系统基于 G=B+M 模型，提供6种核心策略：

#### Sell Put 策略

| 策略名称 | 条件 | 风险等级 | 说明 |
|---------|------|---------|------|
| 🛡️ 安全建仓 | B>=6, 行权价<=支撑位*1.02, 年化收益>=15% | Low | 基本面优秀，在关键支撑位建仓 |
| 💎 价值挖掘 | B>=5, 深度虚值(>8%), 年化收益>=20% | Medium | 寻找被低估的价值机会 |
| 📊 温和建仓 | B>=4, 行权价<支撑位, 年化收益>=12% | Medium | 中等基本面，温和建仓策略 |

**熔断规则**: B分数<3时，⛔ 禁止卖Put操作（基本面恶化，风险极高）

#### Sell Call 策略（Covered Call）

| 策略名称 | 条件 | 风险等级 | 说明 |
|---------|------|---------|------|
| 📤 高位增收 | B>=6, M>=7, 价格>支撑位*1.15, 年化收益>=8% | Low | 优质股票高位，增强收益 |
| ⚠️ 高风险做空 | B<5, M>=7, 年化收益>=25% | High | 垃圾股被炒高，高风险策略 |
| 💼 适度增收 | B>=5, M>=5, 年化收益>=6% | Medium | 中等质量股票，适度增收 |

### 3. 关键指标
- **年化收益 (AR)**: 期权策略的年化回报率
- **安全边际**: 当前价格与行权价的差距（价格差异百分比）
- **支撑位 (MA200)**: 基于200日均线的关键支撑，用于判断建仓位置
- **Delta**: 期权希腊值，衡量价格敏感性
- **DTE (Days To Expiry)**: 到期天数，系统筛选7-90天的合约
- **权利金 (Premium)**: 期权价格，系统过滤低于$0.05的噪音合约

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

本模块完全遵循 AlphaGBM 设计系统规范：

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
  "alpha_g_score": {
    "G": 72,
    "B": 80,
    "M": 65
  },
  "current_price": 135.50,
  "support_level": 120.5,
  "warnings": [],
  "recommended_options": [
    {
      "signal": "🛡️ Sell Put: 安全建仓",
      "option_action": "Sell Put",
      "required_condition": "💵 现金 $13,000",
      "risk_level": "Low",
      "expiry": "2024-12-20",
      "strike": 130.0,
      "annualized_return": 18.5,
      "safety_margin": 4.07,
      "premium": 260.0,
      "delta": -0.35
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
  - AlphaGBM Design System (自定义样式)

## ⚠️ 注意事项

1. **API限制**: Polygon 免费版有调用次数限制，建议适度使用
2. **数据延迟**: 免费API可能有15分钟延迟
3. **风险提示**: 本系统仅供研究学习，不构成投资建议
4. **独立运行**: 本模块与主系统独立，互不影响

## 📝 更新日志

### v1.1.0 (2025-01-XX)
- ✅ **重构期权选择逻辑**：创建 `OptionsStrategySelector` 类，代码结构更清晰
- ✅ **策略系统优化**：从4个策略扩展到6个策略，覆盖更多场景
- ✅ **合约验证改进**：增加DTE范围检查（7-90天），过滤不合理合约
- ✅ **排序逻辑优化**：推荐优先 → 年化收益 → 低风险优先
- ✅ **代码模块化**：分离Put和Call策略评估逻辑，便于维护和扩展

### v1.0.0 (2025-12-26)
- ✅ 初始版本发布
- ✅ 实现 AlphaGBM (G=B+M) 核心模型
- ✅ 集成 Polygon 期权数据
- ✅ 匹配 AlphaGBM 设计系统
- ✅ 智能策略推荐

## 🤝 支持

如有问题，请联系开发团队或提交 Issue。

---

**© 2025 Alpha GBM. 基于 G=B+M 投资框架**

