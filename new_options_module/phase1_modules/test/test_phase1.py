# phase1_modules/test/test_phase1.py

import sys
import os
import random

# 添加父目录到路径以便导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vrp_calculator import VRPCalculator
from risk_adjuster import RiskAdjuster, RiskLevel

def test_vrp_module():
    print(">>> 开始测试 VRP 模块...")
    calculator = VRPCalculator()
    
    # 1. 基础 VRP 计算
    vrp = calculator.calculate_vrp(0.30, 0.25)
    assert abs(vrp - 0.05) < 1e-9, f"VRP计算错误: {vrp}"
    print("  [通过] VRP 基础计算")
    
    # 2. IV Rank 计算
    iv_history = [0.20, 0.25, 0.30, 0.35, 0.40]
    # 0.30 在列表中间，Rank 应该是 40% 或 60% 取决于算法细节（左侧插入）
    iv_rank = calculator.calculate_iv_rank(0.30, iv_history)
    print(f"  IV Rank for 0.30 in {iv_history}: {iv_rank}%")
    assert 0 <= iv_rank <= 100
    print("  [通过] IV Rank 计算")
    
    # 3. 波动率预测 (EWMA/GARCH)
    # 生成模拟价格序列 (随机游走)
    price_history = [100.0]
    for _ in range(60):
        change = (random.random() - 0.5) * 2  # -1 to +1
        price_history.append(price_history[-1] + change)
        
    rv = calculator.forecast_realized_volatility(price_history, method="ewma")
    print(f"  预测 RV (EWMA): {rv:.4f}")
    assert 0 < rv < 2.0, "RV 预测值异常"
    print("  [通过] RV 预测")
    
    # 4. 完整结果测试
    result = calculator.calculate_vrp_result(0.30, price_history, iv_history)
    assert result.recommendation in ["buy", "sell", "neutral"]
    print(f"  完整建议: {result.recommendation}, VRP: {result.vrp:.4f}")
    print("  [通过] VRP 完整流程")

def test_risk_module():
    print("\n>>> 开始测试 Risk 模块...")
    adjuster = RiskAdjuster()
    
    # 1. 期望值测试
    # 80% 赚 $100, 20% 亏 $500 -> EV = 80 - 100 = -20
    ev = adjuster.calculate_expected_value(0.8, 100, 500)
    assert abs(ev - (-20)) < 0.001
    print(f"  期望值计算 (应为 -20): {ev}")
    print("  [通过] 期望值计算")
    
    # 2. 风险调整后期望值
    rae = adjuster.calculate_risk_adjusted_expectancy(100, 5000)
    assert abs(rae - 0.02) < 0.001
    print("  [通过] RAE 计算")
    
    # 3. 完整分析测试
    analysis = adjuster.analyze_risk(
        win_prob=0.85,
        avg_profit=100,
        avg_loss=5000,
        max_loss=10000
    )
    print(f"  风险等级: {analysis.risk_level}")
    print(f"  警告信息: {analysis.tail_risk_warning}")
    assert isinstance(analysis.risk_level, RiskLevel)
    print("  [通过] 风险综合分析")

if __name__ == "__main__":
    try:
        test_vrp_module()
        test_risk_module()
        print("\n🎉 所有测试用例通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
