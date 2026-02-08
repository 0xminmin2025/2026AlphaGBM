# 已知问题与改进建议

> 代码审查和日常开发中发现的问题跟踪

---

## 代码审查发现

| # | 文件 | 问题描述 | 严重程度 | 状态 | 修复方案 |
|---|------|---------|---------|------|---------|
| 1 | app/__init__.py:102-121 | Admin endpoints `/api/admin/trigger-*` lacked authentication | P0 | **Verified** | Added ADMIN_SECRET_KEY header check |
| 2 | app/scheduler.py:30 | Exchange rate cache `.seconds` → `.total_seconds()` bug | P1 | **Verified** | Changed to `.total_seconds()` |
| 3 | app/services/payment_service.py:163 | Bare `except:` catches SystemExit/KeyboardInterrupt | P1 | **Verified** | Changed to `except Exception:` |
| 4 | app/utils/auth.py + decorators.py | Auth logic duplicated between `require_auth` and `check_quota` (~120 lines) | P2 | **Open** | Refactor to shared `_authenticate()` function |
| 5 | app/utils/auth.py:13 | Token cache dict has no size limit; cleanup every 50th call | P2 | **Open** | Add max size (e.g., 10000) + LRU eviction |
| 6 | app/utils/decorators.py:132 | `check_quota` doesn't use token cache — every call hits Supabase API | P2 | **Open** | Reuse `get_cached_user()` from auth.py |
| 7 | app/utils/decorators.py:226-243 | Dead code — incomplete credit info injection into response | P3 | **Open** | Remove dead code or implement feature |
| 8 | app/scheduler.py:21-22 | Exchange rate cache globals lack thread safety | P2 | **Open** | Add `threading.Lock` around cache reads/writes |

### 严重程度定义

| 等级 | 含义 | 处理要求 |
|------|------|---------|
| **P0 - Critical** | 安全漏洞、数据丢失风险、生产环境崩溃 | 立即修复 |
| **P1 - High** | 功能错误、资金相关逻辑缺陷 | 当前迭代修复 |
| **P2 - Medium** | 性能问题、边界条件未处理、代码规范 | 下个迭代修复 |
| **P3 - Low** | 代码风格、文档缺失、优化建议 | 排期处理 |

### 状态定义

| 状态 | 含义 |
|------|------|
| **Open** | 已发现，待修复 |
| **In Progress** | 修复中 |
| **Fixed** | 已修复，待验证 |
| **Verified** | 已验证关闭 |
| **Won't Fix** | 不修复（附原因） |

---

## 架构层面改进建议

| # | 领域 | 建议 | 优先级 | 状态 |
|---|------|------|--------|------|
| A01 | 数据源 | 增加宏观指标 Fallback（VIX/Gold/Oil/TNX 当前无 Fallback） | High | Open |
| A02 | 数据源 | 接入 defeatbeta `calendar()` 作为财报日期 Fallback | High | Open |
| A03 | 数据源 | 替换 Hardcoded Fed 会议日期为 API 数据源 | Medium | Open |
| A04 | 期权 | 减少 Tiger API 单点依赖，增加第二数据源 | High | Open |
| A05 | 安全 | 确保所有 API Key 仅通过环境变量注入 | High | Open |

---

*本文件持续更新，每次代码审查后补充新发现*
*最后更新: 2026-02-08*
