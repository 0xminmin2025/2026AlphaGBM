# Task Queue 模块

## 1. 模块概述

任务队列模块基于 Python `ThreadPoolExecutor` 实现异步任务处理，是整个分析系统的核心调度引擎。

**核心特性**:

- **3 worker threads** — 最多同时处理 3 个分析任务
- **Priority queue** — 支持任务优先级排序
- **UUID 任务追踪** — 每个任务分配唯一 UUID，支持状态轮询
- **缓存加速** — 命中缓存时模拟进度条 (fake progress)，提升用户体验
- **数据库持久化** — 任务状态及结果写入数据库，支持历史查询

**文件**: `app/services/task_queue.py` (~647 lines)

---

## 2. TaskQueue 类

### 2.1 初始化

```python
class TaskQueue:
    def __init__(self, app=None):
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.tasks = {}           # task_id -> task_info dict
        self.priority_queue = PriorityQueue()
        self.running = False
        self.app = app
```

### 2.2 核心方法

| 方法 | 说明 |
|------|------|
| `start()` | 启动 worker loop，开始消费任务队列 |
| `stop()` | 优雅关闭：等待当前任务完成，关闭 executor |
| `create_task(task_type, params)` | 创建新任务，返回 UUID task_id |
| `get_task_status(task_id)` | 查询任务当前状态、进度、结果 |
| `get_user_tasks(limit)` | 获取最近的任务列表 |
| `_worker_loop()` | Worker 主循环：从队列取任务并执行 |

### 2.3 create_task 流程

```
create_task(task_type, params)
    |- 生成 UUID task_id
    |- 检查缓存命中 -> 设置 cache_mode
    |- 构建 task_info dict (status=PENDING, progress=0, cache_mode)
    |- 写入 AnalysisTask 数据库记录
    |- 放入 priority_queue
    |- 返回 task_id (UUID string)
```

---

## 3. 任务类型

| 类型常量 | 说明 | 优先级 |
|---------|------|--------|
| `STOCK_ANALYSIS` | 股票综合分析 (含 AI 报告) | 1 (最高) |
| `OPTION_ANALYSIS` | 期权基础分析 | 2 |
| `ENHANCED_OPTION_ANALYSIS` | 增强期权分析 (含 Greeks 计算) | 2 |

---

## 4. 缓存模式 (Cache Mode)

### 4.1 None — 正常模式

缓存未命中，需完整执行分析流程。实际调用 DataProvider + AI Service，进度实时更新。

### 4.2 'cached' — 缓存命中模式

分析结果已在 `DailyAnalysisCache` 或 History 表中。模拟 5-8 秒的 fake progress (0% -> 30% -> 60% -> 90% -> 100%)，最终直接返回缓存数据。

### 4.3 'waiting' — 等待依赖模式

相同 ticker 的分析任务正在进行中。当前任务等待前序任务完成后共享结果，避免重复分析。

---

## 5. 任务生命周期

### 5.1 状态流转

```
PENDING --> PROCESSING --> COMPLETED
                |
                +--> FAILED
```

| 状态 | 含义 |
|------|------|
| `PENDING` | 已入队列，等待 worker 拾取 |
| `PROCESSING` | worker 正在执行，progress 实时更新 |
| `COMPLETED` | 执行成功，result 字段包含分析结果 |
| `FAILED` | 执行失败，error 字段包含错误信息 |

### 5.2 进度追踪

| 进度区间 | current_step 示例 |
|---------|-------------------|
| 0-10% | `"Initializing analysis..."` |
| 10-30% | `"Fetching market data..."` |
| 30-50% | `"Calculating technical indicators..."` |
| 50-70% | `"Running AI analysis..."` |
| 70-90% | `"Generating report..."` |
| 90-100% | `"Finalizing results..."` |

前端通过轮询 `get_task_status` 接口展示进度条和步骤文字。

---

## 6. 处理路径

Worker 根据 `cache_mode` 和 `task_type` 选择不同的处理路径：

| 方法 | 说明 |
|------|------|
| `_process_cached_task` | 从缓存读取数据，模拟进度动画后返回 |
| `_process_waiting_task` | 轮询等待前序任务完成 (最长 300 秒)，超时降级为正常模式 |
| `_process_stock_analysis` | 完整股票分析: DataProvider -> 技术指标 -> AI 报告 -> 写入 History |
| `_process_options_analysis` | 完整期权分析: 期权链 -> Greeks -> 策略推荐 -> 写入 History |

---

## 7. 数据库集成

### 7.1 AnalysisTask Model

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String (UUID) | 任务唯一标识 |
| `task_type` | String | 任务类型 |
| `status` | String | 当前状态 |
| `params` | JSON | 任务参数 |
| `result` | JSON | 分析结果 (完成后填充) |
| `error` | Text | 错误信息 (失败后填充) |
| `created_at` | DateTime | 创建时间 |
| `completed_at` | DateTime | 完成时间 |

### 7.2 关联 History 表

| 表 | 说明 |
|----|------|
| `StockAnalysisHistory` | 股票分析历史记录，含完整 AI 报告 |
| `OptionsAnalysisHistory` | 期权分析历史记录，含策略推荐 |
| `DailyAnalysisCache` | 当日分析缓存，次日自动过期 |

---

## 8. 文件路径清单

| 文件路径 | 说明 | 大致行数 |
|---------|------|---------|
| `app/services/task_queue.py` | TaskQueue 核心实现 | ~647 |
| `app/models/analysis.py` | AnalysisTask 等数据模型 | ~100 |
| `app/routes/analysis_routes.py` | 任务创建及查询 API | ~200 |

---

## 9. 注意事项

- Worker 线程数 (3) 与外部 API 的 rate limit 需协调，避免被限流
- `tasks` 内存 dict 在进程重启后会丢失，但数据库记录保留
- Fake progress 的延时范围可调整，当前为 1.0-2.0 秒随机
- 等待模式超时 (300s) 后会自动降级重新执行，确保任务不会永久挂起
- 所有数据库操作在 Flask app context 中执行
