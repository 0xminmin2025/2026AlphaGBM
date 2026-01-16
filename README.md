# AlphaG - 智能股票与期权分析系统

一个基于 AI 的量化投资分析平台，提供专业的股票分析和期权研究功能。

## 📋 目录

- [系统概述](#系统概述)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [算法标准](#算法标准)
- [开发指南](#开发指南)
- [部署说明](#部署说明)

## 🎯 系统概述

AlphaG 是一个现代化的量化投资分析平台，集成了：

- **股票分析**：基于 AlphaG (G=B+M) 模型的智能股票分析
- **期权研究**：实时期权链数据分析和量化评分
- **AI 报告**：使用 Google Gemini AI 生成专业投资分析报告
- **投资组合管理**：持仓跟踪、盈亏计算、风格分析
- **订阅系统**：基于 Stripe 的订阅和积分系统

## ✨ 核心功能

### 股票分析

- **多市场支持**：美股、港股、A股
- **AlphaG 模型**：收益 = 基本面(B) + 动量(M)
- **风险评分**：0-10 分风险评分系统
- **EV 期望值模型**：多时间视界期望值计算
- **目标价格计算**：多维度估值模型
- **AI 分析报告**：专业的投资建议报告

### 期权分析

- **实时期权链**：通过 Tiger OpenAPI 获取实时数据
- **量化评分**：流动性、IV 排名、风险调整评分
- **VRP 计算**：波动率风险溢价分析
- **策略推荐**：买入看涨/看跌、卖出看涨/看跌策略
- **增强分析**：深度期权链分析

### 投资组合

- **持仓管理**：添加、编辑、删除持仓
- **盈亏跟踪**：每日盈亏自动计算
- **风格分析**：按投资风格（质量/价值/成长/趋势）分类统计
- **历史记录**：完整的分析历史记录

## 🏗️ 技术架构

### 前端技术栈

- **框架**：React 19 + TypeScript
- **构建工具**：Vite 7
- **UI 组件库**：Radix UI + Tailwind CSS
- **状态管理**：React Hooks + Context API
- **路由**：React Router 7
- **国际化**：react-i18next
- **HTTP 客户端**：Axios

### 后端技术栈

- **框架**：Flask 3.0
- **数据库**：PostgreSQL (Supabase) / SQLite (开发)
- **ORM**：SQLAlchemy 3.1
- **认证**：Supabase Auth + JWT
- **任务队列**：自定义多线程任务队列
- **定时任务**：APScheduler
- **支付**：Stripe
- **数据源**：
  - Yahoo Finance (yfinance)
  - Tiger OpenAPI (期权数据)
  - Alpha Vantage (备用数据源)

### 系统架构

```
┌─────────────────┐
│   React Frontend │
│   (TypeScript)   │
└────────┬─────────┘
         │ HTTP/JSON
         ▼
┌─────────────────┐
│   Flask Backend  │
│    (Python 3.13) │
└────────┬─────────┘
         │
    ┌────┴────┐
    │        │
    ▼        ▼
┌────────┐ ┌──────────┐
│Supabase│ │  Stripe  │
│  Auth  │ │ Payment  │
└────────┘ └──────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+
- Yarn 或 npm

### 安装步骤

1. **克隆仓库**

```bash
git clone git@github.com:0xminmin2025/AlphaG.git
cd 2026AlphaGBM_stockoption
```

2. **配置后端**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

3. **配置环境变量**

创建 `backend/.env` 文件：

```env
# Google Gemini API
GOOGLE_API_KEY=your_api_key

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
POSTGRES_URL=your_postgres_url

# JWT
JWT_SECRET_KEY=your_secret_key

# Stripe (可选)
STRIPE_SECRET_KEY=your_stripe_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret

# Tiger OpenAPI (期权数据)
TIGER_API_KEY=your_tiger_key
TIGER_SECRET_KEY=your_tiger_secret
```

4. **配置前端**

```bash
cd frontend
yarn install
```

5. **启动服务**

**后端**：
```bash
cd backend
source venv/bin/activate
python run.py
```

**前端**：
```bash
cd frontend
yarn dev
```

6. **访问应用**

- 前端：http://localhost:5173
- 后端 API：http://127.0.0.1:5002/api

## 📁 项目结构

```
.
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── analysis/          # 分析模块
│   │   │   ├── stock_analysis/    # 股票分析
│   │   │   └── options_analysis/   # 期权分析
│   │   ├── services/          # 业务逻辑
│   │   ├── models.py          # 数据模型
│   │   ├── config.py          # 配置
│   │   └── constants.py       # 常量
│   ├── run.py                 # 启动入口
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── pages/             # 页面
│   │   ├── lib/               # 工具库
│   │   └── types/             # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                       # 文档
│   └── DESIGN_STANDARDS.md    # 设计标准
│
└── README.md                  # 本文档
```

## 📚 API 文档

### 股票分析

- `POST /api/stock/analyze` - 分析股票
- `GET /api/stock/history` - 获取分析历史
- `GET /api/stock/history/<id>` - 获取详细分析

### 期权分析

- `POST /api/options/chain` - 获取期权链
- `POST /api/options/analyze` - 分析期权
- `GET /api/options/expirations` - 获取到期日

### 用户相关

- `GET /api/user/profile` - 获取用户信息
- `GET /api/user/credits` - 获取积分余额
- `GET /api/user/transactions` - 获取交易记录

### 投资组合

- `GET /api/portfolio/holdings` - 获取持仓
- `POST /api/portfolio/holdings` - 添加持仓
- `PUT /api/portfolio/holdings/<id>` - 更新持仓
- `DELETE /api/portfolio/holdings/<id>` - 删除持仓

详细 API 文档请查看：`backend/app/docs/openapi.yaml`

## 📊 算法标准

系统采用标准化的算法框架，确保分析结果的一致性和可追溯性：

- [股票算法标准](./backend/app/analysis/stock_analysis/ALGORITHM_STANDARDS.md)
- [期权算法标准](./backend/app/analysis/options_analysis/ALGORITHM_STANDARDS.md)
- [设计标准](./docs/DESIGN_STANDARDS.md)

## 🛠️ 开发指南

### 代码规范

- **Python**：遵循 PEP 8，使用 Black 格式化
- **TypeScript**：使用 ESLint，遵循 Airbnb 规范
- **提交信息**：使用 Conventional Commits 格式

### 测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
yarn test
```

### 数据库迁移

```bash
cd backend
python create_history_table.py
python create_async_tables.py
```

## 🚢 部署说明

### Docker 部署

```bash
docker-compose up -d
```

### 生产环境

1. 配置环境变量
2. 使用 Gunicorn 运行后端
3. 构建前端并部署到 CDN

详细部署文档请参考 `backend/Dockerfile` 和 `docker-compose.yml`

## 📝 许可证

本项目仅供学习和研究使用。

## 👤 作者

- **minmin** - [GitHub](https://github.com/0xminmin2025)
- **Email**: nftventure@gmail.com

## 🙏 致谢

- [Yahoo Finance](https://finance.yahoo.com/) - 股票数据源
- [Google Gemini AI](https://ai.google.dev/) - AI 分析能力
- [Tiger OpenAPI](https://www.tigerbrokers.com/) - 期权数据源
- [Supabase](https://supabase.com/) - 认证和数据库服务

---

**免责声明**: 本系统仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。
