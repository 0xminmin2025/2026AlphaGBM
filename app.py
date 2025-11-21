from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from analysis_engine import get_market_data, analyze_risk_and_position, calculate_market_sentiment, calculate_target_price
from ai_service import get_gemini_analysis

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    req_data = request.json
    ticker = req_data.get('ticker', '').upper()
    style = req_data.get('style', 'quality')
    
    print(f"收到分析请求: {ticker}, 风格: {style}")

    # 1. 获取硬数据
    from analysis_engine import normalize_ticker
    normalized_ticker = normalize_ticker(ticker)
    
    try:
        market_data = get_market_data(ticker)
    except Exception as e:
        print(f"获取数据时发生异常: {e}")
        import traceback
        traceback.print_exc()
        error_msg = f'数据获取失败: {str(e)}'
        if normalized_ticker != ticker:
            error_msg += f'\n已尝试标准化为: {normalized_ticker}'
        return jsonify({'success': False, 'error': error_msg}), 400
    
    if not market_data:
        error_msg = f'找不到股票代码 "{ticker}" 或数据获取失败'
        if normalized_ticker != ticker:
            error_msg += f'\n已尝试标准化为: {normalized_ticker}'
        error_msg += '\n\n可能的原因：\n1. 股票代码不存在\n2. 网络连接问题\n3. 数据源暂时不可用\n\n请尝试：\n- 港股代码：2525 或 2525.HK\n- 美股代码：AAPL\n- A股代码：600519'
        return jsonify({'success': False, 'error': error_msg}), 400

    # 2. 计算硬逻辑
    try:
        risk_result = analyze_risk_and_position(style, market_data)
    except Exception as e:
        print(f"计算风险评分时发生异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'风险计算失败: {str(e)}'}), 500
    
    # 3. 计算市场情绪评分
    try:
        market_sentiment = calculate_market_sentiment(market_data)
        market_data['market_sentiment'] = market_sentiment
    except Exception as e:
        print(f"计算市场情绪时发生异常: {e}")
        import traceback
        traceback.print_exc()
        market_data['market_sentiment'] = 5.0  # 使用默认值
    
    # 4. 计算目标价格
    try:
        target_price = calculate_target_price(market_data, risk_result, style)
        market_data['target_price'] = target_price
    except Exception as e:
        print(f"计算目标价格时发生异常: {e}")
        import traceback
        traceback.print_exc()
        market_data['target_price'] = market_data['price']  # 使用当前价格作为默认值

    # 5. 调用 Gemini AI (这可能需要几秒钟)
    try:
        ai_report = get_gemini_analysis(ticker, style, market_data, risk_result)
    except Exception as e:
        print(f"AI分析时发生异常: {e}")
        import traceback
        traceback.print_exc()
        # 使用备用分析
        from ai_service import get_fallback_analysis
        ai_report = get_fallback_analysis(ticker, style, market_data, risk_result)

    # 确保所有数据都可以JSON序列化
    def make_json_serializable(obj):
        """递归转换对象为JSON可序列化格式"""
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(item) for item in obj]
        elif isinstance(obj, (bool, int, float, str)) or obj is None:
            return obj
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        else:
            return str(obj)
    
    # 转换数据
    serializable_data = make_json_serializable(market_data)
    serializable_risk = make_json_serializable(risk_result)
    
    return jsonify({
        'success': True,
        'data': serializable_data,
        'risk': serializable_risk,
        'report': ai_report
    })

if __name__ == '__main__':
    print("启动投资分析系统...")
    print("服务器地址: http://127.0.0.1:5001")
    print("注意: 端口5000被Apple AirPlay占用，已改用5001端口")
    app.run(debug=True, port=5001, host='0.0.0.0', threaded=True)

