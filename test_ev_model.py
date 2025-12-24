#!/usr/bin/env python3
"""
EV 模型测试脚本

测试 EV（期望值）模型的计算和展示功能
"""

import requests
import json
import sys

# 配置
BASE_URL = "http://localhost:5002"
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "test123456"
}

def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def register_and_login():
    """注册并登录测试用户"""
    print_section("1. 用户注册和登录")
    
    # 尝试登录
    login_response = requests.post(
        f"{BASE_URL}/api/login",
        json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
    )
    
    if login_response.status_code == 200:
        result = login_response.json()
        if result.get('success'):
            print("✅ 登录成功")
            return result.get('access_token')
    
    print("⚠️ 用户不存在，尝试注册...")
    
    # 注册新用户（需要邮箱验证码，这里假设使用简化流程）
    # 如果注册失败，使用默认测试账号
    print("💡 使用现有测试账号")
    
    # 再次尝试登录
    login_response = requests.post(
        f"{BASE_URL}/api/login",
        json={
            "email": "test@test.com",  # 使用数据库初始化时创建的测试账号
            "password": "test123"
        }
    )
    
    if login_response.status_code == 200:
        result = login_response.json()
        if result.get('access_token'):  # 修改：检查 access_token 而不是 success
            print("✅ 使用测试账号登录成功")
            return result.get('access_token')
    
    print("❌ 登录失败，无法继续测试")
    print(f"响应: {login_response.text}")
    return None

def test_analyze_with_ev(token, ticker="AAPL", style="quality"):
    """测试包含 EV 模型的分析功能"""
    print_section(f"2. 分析股票：{ticker} (风格: {style})")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"⏳ 正在分析 {ticker}，请稍候...")
    print("   （包括数据获取、风险计算、EV 模型、AI 分析）")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            headers=headers,
            json={
                "ticker": ticker,
                "style": style,
                "onlyHistoryData": False
            },
            timeout=120  # 2分钟超时
        )
        
        if response.status_code != 200:
            print(f"❌ 分析失败: HTTP {response.status_code}")
            print(f"响应: {response.text[:500]}")
            return False
        
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ 分析失败: {result.get('error', '未知错误')}")
            return False
        
        print("\n✅ 分析成功！\n")
        
        # 提取数据
        data = result.get('data', {})
        risk = result.get('risk', {})
        ev_model = data.get('ev_model', {})
        
        # 显示基本信息
        print_section("基本信息")
        print(f"股票代码: {data.get('symbol')}")
        print(f"公司名称: {data.get('name')}")
        print(f"当前价格: ${data.get('price', 0):.2f}")
        print(f"行业: {data.get('sector')} - {data.get('industry')}")
        
        # 显示风险评估
        print_section("风险评估")
        print(f"风险等级: {risk.get('level')}")
        print(f"风险评分: {risk.get('score')}/10")
        print(f"建议仓位: {risk.get('suggested_position')}%")
        
        # 显示市场情绪
        sentiment = data.get('market_sentiment', {})
        if isinstance(sentiment, dict):
            sentiment_score = sentiment.get('综合情绪分数', 5.0)
        else:
            sentiment_score = sentiment
        print(f"市场情绪: {sentiment_score:.1f}/10")
        
        # 显示 EV 模型结果
        print_section("📊 EV 期望值模型")
        
        if ev_model.get('error'):
            print(f"❌ EV 模型计算失败: {ev_model.get('error')}")
            return False
        
        # 加权综合 EV
        ev_weighted_pct = ev_model.get('ev_weighted_pct', 0)
        ev_score = ev_model.get('ev_score', 5.0)
        print(f"\n【综合期望值】")
        print(f"  加权 EV: {ev_weighted_pct:+.2f}%")
        print(f"  EV 评分: {ev_score:.1f}/10")
        
        # 各时间视界
        print(f"\n【多时间视界分析】")
        
        ev_1week = ev_model.get('ev_1week', {})
        if ev_1week:
            print(f"\n  📅 1周期望值:")
            print(f"     EV: {ev_1week.get('ev_pct', 0):.2f}%")
            print(f"     上涨概率: {ev_1week.get('probability_up', 0)*100:.0f}%")
            print(f"     下跌概率: {ev_1week.get('probability_down', 0)*100:.0f}%")
            print(f"     预期上涨: {ev_1week.get('upside_pct', 0)*100:+.2f}%")
            print(f"     预期下跌: {ev_1week.get('downside_pct', 0)*100:+.2f}%")
            print(f"     盈亏比: {ev_1week.get('risk_reward_ratio', 0):.2f}")
        
        ev_1month = ev_model.get('ev_1month', {})
        if ev_1month:
            print(f"\n  📅 1月期望值:")
            print(f"     EV: {ev_1month.get('ev_pct', 0):.2f}%")
            print(f"     上涨概率: {ev_1month.get('probability_up', 0)*100:.0f}%")
            print(f"     下跌概率: {ev_1month.get('probability_down', 0)*100:.0f}%")
        
        ev_3months = ev_model.get('ev_3months', {})
        if ev_3months:
            print(f"\n  📅 3月期望值:")
            print(f"     EV: {ev_3months.get('ev_pct', 0):.2f}%")
            print(f"     上涨概率: {ev_3months.get('probability_up', 0)*100:.0f}%")
            print(f"     下跌概率: {ev_3months.get('probability_down', 0)*100:.0f}%")
        
        # EV 推荐
        recommendation = ev_model.get('recommendation', {})
        print(f"\n【EV 推荐】")
        print(f"  行动: {recommendation.get('action', 'HOLD')}")
        print(f"  理由: {recommendation.get('reason', '')}")
        print(f"  信心度: {recommendation.get('confidence', 'low')}")
        
        # 加权公式说明
        weights = ev_model.get('weights', {})
        print(f"\n【加权公式】")
        print(f"  综合EV = 1周EV×{weights.get('1week', 0.5)*100:.0f}% + "
              f"1月EV×{weights.get('1month', 0.3)*100:.0f}% + "
              f"3月EV×{weights.get('3months', 0.2)*100:.0f}%")
        
        # 显示止损价格
        print_section("交易建议")
        print(f"当前价格: ${data.get('price', 0):.2f}")
        print(f"目标价格: ${data.get('target_price', 0):.2f}")
        print(f"止损价格: ${data.get('stop_loss_price', 0):.2f}")
        print(f"止损方法: {data.get('stop_loss_method', '未知')}")
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时（2分钟）")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试流程"""
    print("\n" + "🚀"*30)
    print("  EV 期望值模型 - 功能测试")
    print("🚀"*30)
    
    # 1. 登录
    token = register_and_login()
    if not token:
        sys.exit(1)
    
    # 2. 测试不同股票
    test_stocks = [
        ("AAPL", "quality"),   # 苹果 - 质量风格
        # ("NVDA", "growth"),    # 英伟达 - 成长风格
        # ("TSLA", "momentum"),  # 特斯拉 - 趋势风格
    ]
    
    success_count = 0
    for ticker, style in test_stocks:
        if test_analyze_with_ev(token, ticker, style):
            success_count += 1
    
    # 总结
    print_section("测试总结")
    print(f"✅ 成功: {success_count}/{len(test_stocks)}")
    print(f"{'❌ 失败: ' + str(len(test_stocks) - success_count) if success_count < len(test_stocks) else ''}")
    
    if success_count == len(test_stocks):
        print("\n🎉 所有测试通过！EV 模型运行正常！")
        print("\n💡 现在可以在浏览器中访问 http://localhost:5002 查看完整的可视化界面")
    else:
        print("\n⚠️ 部分测试失败，请检查日志")
        sys.exit(1)

if __name__ == "__main__":
    main()

