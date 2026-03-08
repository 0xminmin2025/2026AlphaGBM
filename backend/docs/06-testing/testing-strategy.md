# 测试策略

> AlphaGBM Backend 测试体系总纲

---

## 1. 测试策略概述

本项目采用 **pytest** 作为测试框架，配合 **pytest-mock** 和 **unittest.mock** 对所有外部依赖进行 Mock，确保测试套件可完全离线运行，不依赖任何外部 API 或第三方服务。

### 核心原则

| 原则 | 说明 |
|------|------|
| **离线可运行** | 所有外部 HTTP 调用均被 Mock，CI/CD 环境无需网络 |
| **快速反馈** | 单元测试目标 < 30 秒完成全套运行 |
| **确定性** | 固定 seed / 固定时间 / 固定数据，消除 flaky tests |
| **隔离性** | 每个测试用例独立，不共享数据库状态 |

---

## 2. 测试分层

```
┌─────────────────────────────────────────┐
│          Integration Tests              │  API 端点完整流程
│     (Flask test client → route →        │  含数据库读写、认证校验
│      service → mock external)           │
├─────────────────────────────────────────┤
│            Unit Tests                   │  单个函数 / 单个类
│     (纯逻辑验证, mock 所有依赖)          │  不涉及 Flask app context
└─────────────────────────────────────────┘
```

### 2.1 Unit Tests（单元测试）

- **目标**: 验证单个函数或类的逻辑正确性
- **范围**: services, models, scoring algorithms, decorators, utilities
- **特点**: 不需要 Flask app context（除 model 测试），不涉及 HTTP 请求
- **运行速度**: 毫秒级

### 2.2 Integration Tests（集成测试）

- **目标**: 验证 API 端点的完整请求-响应流程
- **范围**: `/api/stock/*`, `/api/options/*`, `/api/payment/*`, `/api/auth/*`
- **特点**: 使用 Flask test client，涉及路由解析、认证中间件、数据库操作
- **运行速度**: 秒级

---

## 3. Mock 策略

所有外部依赖必须被 Mock，绝不允许测试中发起真实的外部请求。

| 外部依赖 | Mock 方式 | 说明 |
|----------|-----------|------|
| **Supabase Auth** | `unittest.mock.patch` | Mock `supabase.auth.get_user()` 返回固定用户 |
| **Stripe API** | `unittest.mock.patch` | Mock `stripe.checkout.Session.create()` 等方法 |
| **yfinance** | `unittest.mock.patch` | Mock `yf.Ticker().info`, `yf.Ticker().history()` 等 |
| **Tiger API** | `unittest.mock.patch` | Mock `QuoteClient` 方法，返回预定义 DataFrame |
| **Google Gemini** | `unittest.mock.patch` | Mock HTTP POST 请求，返回固定 OCR 结果 |
| **defeatbeta-api** | `unittest.mock.patch` | Mock `DataProvider` 方法 |
| **ExchangeRate-API** | `unittest.mock.patch` | Mock HTTP GET 请求 |
| **Polymarket API** | `unittest.mock.patch` | Mock GraphQL / REST 请求 |
| **AkShare** | `unittest.mock.patch` | Mock `ak.stock_restricted_shares_summary_em()` |
| **requests/httpx** | `unittest.mock.patch` | 兜底 Mock，拦截所有未预期的 HTTP 调用 |

### Mock 数据管理

- 所有 Mock 数据集中存放在 `tests/fixtures/` 目录
- 使用 JSON 文件存储复杂数据（如 option chain, stock info）
- 小型数据直接在 fixture 函数中定义

---

## 4. Fixtures

以下是 `conftest.py` 中需要定义的核心 Fixtures：

| Fixture | Scope | 说明 |
|---------|-------|------|
| `app` | `session` | Flask test app，使用 SQLite in-memory 数据库 |
| `client` | `function` | Flask test client，每个测试函数独立 |
| `db` | `function` | 数据库 session，测试后自动 rollback |
| `mock_supabase` | `function` | Mock Supabase Auth 客户端 |
| `mock_stripe` | `function` | Mock Stripe API 全部方法 |
| `sample_user` | `function` | 预创建的测试用户（含 User 记录） |
| `sample_stock_data` | `session` | 预定义的股票数据 dict（模拟 yfinance.info） |
| `sample_options_data` | `session` | 预定义的期权链 DataFrame |
| `auth_headers` | `function` | 携带有效 Bearer token 的请求头 dict |
| `paid_user` | `function` | 付费用户（含 Subscription + CreditLedger） |
| `free_user` | `function` | 免费用户（无 Subscription） |

### Fixture 依赖关系

```
app (session)
 ├── client (function) ── auth_headers
 ├── db (function)
 │    ├── sample_user
 │    ├── paid_user
 │    └── free_user
 ├── mock_supabase (function)
 └── mock_stripe (function)
```

---

## 5. 覆盖率目标

| 模块 | 目标覆盖率 | 优先级 | 说明 |
|------|-----------|--------|------|
| `payment_service.py` | > 95% | P0 | 涉及金钱，必须高覆盖 |
| `auth.py` | > 95% | P0 | 安全关键路径 |
| `decorators.py` | > 95% | P0 | 额度检查、重试逻辑 |
| `option_scorer.py` | > 90% | P1 | 核心业务算法 |
| `ev_model.py` | > 90% | P1 | 核心业务算法 |
| `api/*` (routes) | > 80% | P1 | API 接口层 |
| `analysis/*` | > 80% | P2 | 分析引擎 |
| `task_queue.py` | > 85% | P1 | 异步任务可靠性 |
| `recommendation_service.py` | > 80% | P2 | 推荐服务 |
| **整体项目** | **> 75%** | - | 最低门槛 |

---

## 6. 测试命名规范

采用三段式命名：`test_{module}_{scenario}_{expected_result}`

### 示例

```python
# payment_service 测试
def test_payment_checkout_valid_plan_returns_session_url():
def test_payment_deduction_insufficient_credits_raises_error():
def test_payment_upgrade_plus_to_pro_prorates_correctly():

# auth 测试
def test_auth_valid_token_returns_user():
def test_auth_expired_token_returns_401():
def test_auth_cache_hit_skips_supabase_call():

# option_scorer 测试
def test_scorer_sell_put_high_iv_returns_high_score():
def test_scorer_liquidity_low_volume_penalizes():
```

### 文件命名

- 每个被测模块对应一个测试文件：`test_{module_name}.py`
- 集成测试以 `test_api_{resource}.py` 命名

---

## 7. 运行命令

```bash
# 运行全部测试（含覆盖率报告）
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# 仅运行单元测试
python -m pytest tests/ -v -m unit

# 仅运行集成测试
python -m pytest tests/ -v -m integration

# 运行单个测试文件
python -m pytest tests/test_payment_service.py -v

# 运行单个测试函数
python -m pytest tests/test_payment_service.py::test_payment_checkout_valid_plan -v

# 跳过慢速测试
python -m pytest tests/ -v -m "not slow"

# 生成 HTML 覆盖率报告
python -m pytest tests/ --cov=app --cov-report=html
```

---

## 8. 测试标记 (Markers)

在 `pytest.ini` 或 `pyproject.toml` 中注册：

```ini
[pytest]
markers =
    unit: 单元测试 - 不需要 Flask app context
    integration: 集成测试 - 需要完整 Flask test client
    slow: 慢速测试 - 运行时间 > 5 秒
```

### 使用方式

```python
import pytest

@pytest.mark.unit
def test_ev_model_calculates_expected_value():
    ...

@pytest.mark.integration
def test_api_stock_analysis_returns_full_report():
    ...

@pytest.mark.slow
def test_full_options_chain_analysis_all_strategies():
    ...
```

---

## 9. CI/CD 集成建议

```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pip install pytest pytest-cov pytest-mock
    python -m pytest tests/ -v --cov=app --cov-report=xml --cov-fail-under=75
  env:
    TESTING: "true"
    DATABASE_URL: "sqlite:///:memory:"
```

### CI 中的关键配置

- `TESTING=true`: 禁用所有外部 API 初始化
- `DATABASE_URL=sqlite:///:memory:`: 使用内存数据库
- `--cov-fail-under=75`: 覆盖率低于 75% 则 CI 失败

---

*最后更新: 2026-02-08*
