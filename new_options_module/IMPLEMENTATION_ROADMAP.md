# Alpha GBM 商业化优化实施路线图

## 一、当前代码结构分析

### 1.1 现有架构
```
tiger_api_wrapper/
├── option_service.py          # FastAPI主服务
├── scoring/
│   └── option_scorer.py       # 期权评分算法
├── models/
│   └── option_models.py       # 数据模型
├── tiger_client.py            # Tiger API客户端
└── frontend.html              # 前端界面
```

### 1.2 当前功能评估

#### ✅ 已有功能
- 基础期权链查询
- 行权概率计算（基于N(d2)）
- 年化收益计算
- 流动性因子计算
- 推荐值算法（基于五大支柱）
- 基础筛选功能

#### ❌ 缺失功能（商业化必需）
- VRP（波动率风险溢价）计算
- 波动率曲面提取
- 策略优化器
- 全市场扫描
- 风险调整后期望值
- 尾部风险分析
- 实时数据接入

---

## 二、Phase 1 实施计划：核心价值提升（优先级最高）

### 2.1 VRP扫描器实现 ⭐⭐⭐

#### 步骤1：创建VRP计算模块
**文件**：`scoring/vrp_calculator.py`

```python
class VRPCalculator:
    """
    波动率风险溢价（VRP）计算器
    VRP = IV - RV_forecast
    """
    
    def calculate_vrp(self, iv: float, rv_forecast: float) -> float:
        """计算VRP"""
        return iv - rv_forecast
    
    def calculate_iv_rank(self, current_iv: float, iv_history: List[float]) -> float:
        """计算IV Rank（0-100）"""
        if not iv_history:
            return 0.0
        sorted_iv = sorted(iv_history)
        rank = bisect.bisect_left(sorted_iv, current_iv) / len(sorted_iv) * 100
        return rank
    
    def forecast_realized_volatility(self, price_history: List[float], window: int = 30) -> float:
        """使用GARCH模型预测已实现波动率"""
        # 实现GARCH(1,1)模型
        # 返回未来波动率预测值
        pass
```

#### 步骤2：集成到推荐算法
**修改**：`frontend.html` 中的 `calculateRecommendation` 函数

```javascript
// 在推荐值计算中加入VRP因子
const vrp = calculateVRP(option, scores, stockPrice);
if (vrp > 0.05) {
    // VRP > 5%，推荐卖出策略（做空波动率）
    score += 10; // 额外加分
}
```

#### 步骤3：UI展示
- 在推荐值旁显示"VRP优势"标签
- 显示IV Rank百分比
- 在详情弹窗中显示VRP分析

**预计工作量**：3-5天

---

### 2.2 风险调整后期望值 ⭐⭐⭐

#### 步骤1：创建风险分析模块
**文件**：`scoring/risk_adjuster.py`

```python
class RiskAdjuster:
    """
    风险调整后期望值计算
    包含尾部风险惩罚
    """
    
    def calculate_expected_value(self, option, scores, stock_price):
        """计算期望值"""
        win_prob = scores.win_rate / 100
        avg_profit = scores.premium_income
        avg_loss = scores.margin_requirement
        
        expected_value = (win_prob * avg_profit) - ((1 - win_prob) * avg_loss)
        return expected_value
    
    def calculate_risk_adjusted_expectancy(self, expected_value, max_loss):
        """风险调整后期望值"""
        if max_loss == 0:
            return 0
        return expected_value / max_loss
    
    def calculate_tail_risk(self, option, scores, stock_price):
        """计算尾部风险（99% VaR）"""
        # 使用历史极端事件数据
        # 计算1%概率下的最大亏损
        pass
```

#### 步骤2：集成到前端
- 在详情弹窗中显示"最大回撤模拟"
- 显示"黑天鹅场景"（1%概率下的亏损）
- 在推荐值中加入风险调整因子

**预计工作量**：2-3天

---

### 2.3 波动率偏斜校正 ⭐⭐

#### 步骤1：创建波动率曲面模块
**文件**：`volatility/volatility_surface.py`

```python
class VolatilitySurface:
    """
    从期权链中提取波动率曲面
    使用SVI模型拟合
    """
    
    def extract_iv_surface(self, option_chain: List[OptionData]) -> Dict:
        """提取IV曲面"""
        # 按行权价和到期日组织IV数据
        # 返回IV矩阵
        pass
    
    def fit_svi_model(self, iv_surface: Dict) -> Dict:
        """拟合SVI模型"""
        # 使用SVI参数化模型
        # 返回模型参数
        pass
    
    def get_local_volatility(self, strike: float, expiry: float, params: Dict) -> float:
        """获取局部波动率"""
        # 根据SVI模型计算特定行权价的波动率
        pass
```

#### 步骤2：修改GBM模拟
- 在模拟中使用局部波动率而非单一波动率
- 根据行权价动态调整波动率

**预计工作量**：5-7天（需要数学库支持）

---

## 三、Phase 2 实施计划：策略能力

### 3.1 策略优化器 ⭐⭐⭐

#### 架构设计
```
strategy/
├── __init__.py
├── optimizer.py          # 主优化器
├── strategy_generator.py # 策略生成器
└── backtester.py         # 回测引擎
```

#### 核心功能
1. **用户输入**：
   - 股票代码
   - 方向性观点（看涨/看跌/中性）
   - 目标价格（可选）
   - 持有时间
   - 风险偏好

2. **优化算法**：
   - 遍历所有可能的策略组合
   - 使用遗传算法或网格搜索
   - 评分标准：夏普比率、ROIC、风险调整后期望值

3. **输出**：
   - 推荐3-5个最优策略
   - 每个策略的详细分析
   - 策略对比表格

**预计工作量**：2-3周

---

### 3.2 全市场扫描器 ⭐⭐⭐

#### 架构设计
```
scanner/
├── __init__.py
└── market_scanner.py
```

#### 核心功能
1. **扫描维度**：
   - IV Rank > 80
   - VRP > 5%
   - 流动性 > 0.6
   - 推荐值 > 70分

2. **筛选器**：
   - 按行业、市值、到期日筛选
   - 按策略类型筛选

3. **输出格式**：
   - 列表视图
   - 卡片视图
   - 可排序

**预计工作量**：1-2周

---

## 四、Phase 3 实施计划：体验升级

### 4.1 盈亏热力图 ⭐⭐

#### 技术实现
- 使用 Plotly.js 或 Chart.js
- 3D热力图或2D热力图
- 交互功能：悬停显示数值、切换策略

**预计工作量**：3-5天

---

### 4.2 概率锥叠加 ⭐⭐

#### 技术实现
- 使用 Lightweight Charts 的插件系统
- 在K线图上叠加概率区间
- 对比GBM预测和市场隐含波动率

**预计工作量**：2-3天

---

### 4.3 自然语言解释 ⭐⭐

#### 技术实现
- 创建解释模板
- 根据计算结果动态填充
- 支持中英文

**预计工作量**：2-3天

---

## 五、技术债务与基础设施

### 5.1 数据基础设施

#### 当前状态
- 使用Tiger API（延时数据）
- 数据获取有限

#### 优化方向
1. **实时数据接入**：
   - 评估Polygon.io、Alpha Vantage等
   - 实现WebSocket实时数据流
   - 数据缓存机制

2. **历史数据存储**：
   - 建立历史IV/RV数据库
   - 存储极端事件数据
   - 用于回测和风险分析

### 5.2 性能优化

#### 当前问题
- 全市场扫描计算量大
- 前端渲染可能卡顿

#### 优化方案
1. **后端优化**：
   - 异步任务队列（Celery）
   - 结果缓存（Redis）
   - 分布式计算（如需要）

2. **前端优化**：
   - 虚拟滚动（大量数据）
   - 懒加载
   - Web Worker（复杂计算）

---

## 六、MVP+ 版本规划

### 6.1 最小可行商业化版本（MVP+）

**核心功能**（必须实现）：
1. ✅ VRP扫描器基础版
2. ✅ 风险调整后期望值
3. ✅ 策略优化器（简化版）
4. ✅ 全市场扫描器（基础版）

**预计时间**：6-8周

### 6.2 完整商业化版本

**所有功能**：
- Phase 1-3 全部功能
- 实时数据接入
- 产品分层（免费/付费）
- API接口

**预计时间**：3-4个月

---

## 七、立即行动项（本周）

### 7.1 代码分析
- [x] 创建优化分支
- [x] 分析当前代码结构
- [x] 创建优化方案文档

### 7.2 开始实施
- [ ] 创建 `scoring/vrp_calculator.py` 模块
- [ ] 创建 `scoring/risk_adjuster.py` 模块
- [ ] 设计VRP计算API接口
- [ ] 修改前端推荐值算法，融入VRP

---

## 八、成功标准

### 8.1 技术指标
- VRP计算准确率 > 90%
- 推荐值准确率提升 > 20%
- 页面加载时间 < 2秒

### 8.2 商业指标
- 付费转化率 > 5%
- 用户留存率（30天）> 40%
- NPS > 50

---

**文档版本**：v1.0  
**创建日期**：2025年1月  
**分支**：feature/commercial-optimization
