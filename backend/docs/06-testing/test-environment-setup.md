# 测试环境搭建指南

> 从零开始配置测试环境

---

## 1. 依赖安装

### 1.1 测试框架依赖

```bash
# 在 backend/ 目录下执行
pip install pytest pytest-cov pytest-mock

# 可选：并行测试加速
pip install pytest-xdist
```

### 1.2 依赖版本说明

| 包名 | 最低版本 | 用途 |
|------|---------|------|
| `pytest` | >= 7.0 | 测试框架 |
| `pytest-cov` | >= 4.0 | 覆盖率报告 |
| `pytest-mock` | >= 3.10 | Mock 便捷接口 |
| `pytest-xdist` | >= 3.0 | 并行测试（可选） |

### 1.3 添加到 requirements-dev.txt

```txt
# backend/requirements-dev.txt
pytest>=7.0
pytest-cov>=4.0
pytest-mock>=3.10
pytest-xdist>=3.0
```

---

## 2. 环境配置

### 2.1 环境变量

测试运行时需要设置以下环境变量，确保不会调用真实外部服务：

```bash
# 必需
export TESTING=true
export DATABASE_URL="sqlite:///:memory:"

# 防止意外调用外部 API（设置无效值）
export SUPABASE_URL="http://localhost:0"
export SUPABASE_KEY="test-key-not-real"
export STRIPE_SECRET_KEY="sk_test_fake"
export STRIPE_WEBHOOK_SECRET="whsec_test_fake"
export GOOGLE_API_KEY="test-key-not-real"
export TIGER_ID="test"
export TIGER_ACCOUNT="test"
```

### 2.2 SQLite In-Memory 数据库

测试中使用 SQLite in-memory 数据库替代 PostgreSQL，优点：

- 无需安装 PostgreSQL
- 每个测试自动创建/销毁，完全隔离
- 运行速度极快

```python
# conftest.py 中的配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['TESTING'] = True
```

### 2.3 禁用外部调用

`TESTING=true` 时应用应跳过以下初始化：

- Supabase client 初始化
- Stripe API 配置
- Tiger API 客户端连接
- Scheduler 启动
- 缓存预热

---

## 3. conftest.py 结构说明

```
tests/
├── conftest.py              # 顶层共享 fixtures
├── fixtures/                # Mock 数据文件
│   ├── stock_info.json      # yfinance ticker.info 模拟数据
│   ├── option_chain.json    # 期权链模拟数据
│   └── stripe_events.json   # Stripe webhook event 模拟数据
├── unit/                    # 单元测试
│   ├── test_models.py
│   ├── test_auth.py
│   ├── test_decorators.py
│   ├── test_payment_service.py
│   ├── test_option_scorer.py
│   ├── test_ev_model.py
│   ├── test_task_queue.py
│   ├── test_recommendation_service.py
│   ├── test_ai_service.py
│   ├── test_narrative_service.py
│   ├── test_stock_engine.py
│   └── test_options_engine.py
└── integration/             # 集成测试
    ├── test_api_stock.py
    ├── test_api_options.py
    ├── test_api_payment.py
    └── test_api_auth.py
```

### conftest.py 核心内容

```python
import pytest
from app import create_app, db as _db

@pytest.fixture(scope='session')
def app():
    """创建 Flask test app，使用 SQLite in-memory"""
    app = create_app(testing=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Flask test client，每个测试独立"""
    return app.test_client()

@pytest.fixture(scope='function')
def db(app):
    """数据库 session，测试后自动 rollback"""
    with app.app_context():
        _db.session.begin_nested()
        yield _db
        _db.session.rollback()

@pytest.fixture
def auth_headers(mock_supabase):
    """携带有效 Bearer token 的请求头"""
    return {'Authorization': 'Bearer test-valid-token'}
```

---

## 4. 运行方式

### 4.1 运行全部测试

```bash
cd backend
python -m pytest tests/ -v
```

### 4.2 运行单个文件

```bash
python -m pytest tests/unit/test_payment_service.py -v
```

### 4.3 运行单个测试函数

```bash
python -m pytest tests/unit/test_payment_service.py::test_payment_checkout_valid_plan -v
```

### 4.4 带覆盖率报告

```bash
# 终端输出（含未覆盖行号）
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# 生成 HTML 报告
python -m pytest tests/ --cov=app --cov-report=html
# 报告路径: htmlcov/index.html

# 生成 XML 报告（CI 用）
python -m pytest tests/ --cov=app --cov-report=xml
```

### 4.5 按标记运行

```bash
# 仅单元测试
python -m pytest tests/ -m unit -v

# 仅集成测试
python -m pytest tests/ -m integration -v

# 排除慢速测试
python -m pytest tests/ -m "not slow" -v
```

### 4.6 并行运行（需 pytest-xdist）

```bash
python -m pytest tests/ -n auto -v
```

---

## 5. CI 集成建议

### 5.1 GitHub Actions 配置

```yaml
# .github/workflows/test.yml
name: Backend Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          cd backend
          python -m pytest tests/ -v \
            --cov=app \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=75
        env:
          TESTING: "true"
          DATABASE_URL: "sqlite:///:memory:"

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml
```

### 5.2 Pre-commit Hook

```bash
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: bash -c 'cd backend && python -m pytest tests/unit/ -q'
      language: system
      pass_filenames: false
      always_run: true
```

### 5.3 覆盖率门槛

- PR 合并要求: 整体覆盖率 >= 75%
- 新代码覆盖率: >= 80%（通过 diff coverage 检查）
- 关键模块（payment, auth）: >= 95%

---

*最后更新: 2026-02-08*
