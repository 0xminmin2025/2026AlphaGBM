from flask import Flask, render_template, request, jsonify
from datetime import datetime
from flask_cors import CORS
import pandas as pd
import logging
import os
import json

# 配置日志
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from analysis_engine import get_market_data, get_ticker_price, analyze_risk_and_position, calculate_market_sentiment, calculate_target_price, calculate_atr_stop_loss
from ai_service import get_gemini_analysis

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stock-price', methods=['GET'])
def get_stock_price():
    """获取单只股票的价格数据"""
    ticker = request.args.get('ticker', '').upper()
    
    if not ticker:
        return jsonify({'success': False, 'error': '请提供股票代码'}), 400
    
    logger.info(f"收到股票价格查询请求: {ticker}, 请求IP: {request.remote_addr}")
    
    price = get_ticker_price(ticker)
    if price is None:
        return jsonify({'success': False, 'error': f'获取股票 {ticker} 价格失败'}), 400
    
    return jsonify({'success': True, 'ticker': ticker, 'price': price,})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    req_data = request.json
    ticker = req_data.get('ticker', '').upper()
    style = req_data.get('style', 'quality')
    onlyHistoryData = req_data.get('onlyHistoryData', False)
    startDate = req_data.get('startDate', None)
    
    logger.info(f"收到分析请求: {ticker}, 风格: {style}, onlyHistoryData: {onlyHistoryData}, 请求IP: {request.remote_addr}")

    # 1. 获取硬数据
    from analysis_engine import normalize_ticker
    normalized_ticker = normalize_ticker(ticker)
    
    try:
        market_data = get_market_data(ticker, onlyHistoryData, startDate)
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

    if onlyHistoryData:
        return jsonify({'success': True, 'data': market_data})


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
    
    # 4.5. 计算动态止损价格（基于ATR）
    try:
        import yfinance as yf
        from analysis_engine import normalize_ticker
        # 重新获取历史数据用于ATR止损计算（只获取最近30天即可）
        normalized_ticker = normalize_ticker(ticker)
        stock = yf.Ticker(normalized_ticker)
        hist = stock.history(period="1mo", timeout=10)  # 获取最近1个月的数据
        
        if not hist.empty and len(hist) >= 15:
            # 使用ATR动态止损
            stop_loss_price = calculate_atr_stop_loss(
                buy_price=market_data['price'],
                hist_data=hist,
                atr_period=14,
                atr_multiplier=2.5,
                min_stop_loss_pct=0.05,
                beta=market_data.get('beta')
            )
            market_data['stop_loss_price'] = stop_loss_price
            market_data['stop_loss_method'] = 'ATR动态止损'
        else:
            # 如果无法计算ATR，使用固定止损
            stop_loss_price = market_data['price'] * 0.85
            market_data['stop_loss_price'] = stop_loss_price
            market_data['stop_loss_method'] = '固定15%止损（数据不足）'
    except Exception as e:
        print(f"计算止损价格时发生异常: {e}")
        import traceback
        traceback.print_exc()
        # 使用固定止损作为默认值
        stop_loss_price = market_data['price'] * 0.85
        market_data['stop_loss_price'] = stop_loss_price
        market_data['stop_loss_method'] = '固定15%止损（计算失败）'

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


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """接收用户反馈"""
    try:
        feedback_data = request.json
        
        # 验证必填字段
        if not feedback_data.get('type'):
            return jsonify({'success': False, 'error': '请选择反馈类型'}), 400
        
        if not feedback_data.get('content'):
            return jsonify({'success': False, 'error': '请填写反馈内容'}), 400
        
        # 添加时间戳和IP地址
        feedback_data['submitted_at'] = datetime.now().isoformat()
        feedback_data['ip_address'] = request.remote_addr
        
        # 保存到文件
        feedback_dir = os.path.join(os.path.dirname(__file__), 'feedback')
        os.makedirs(feedback_dir, exist_ok=True)
        
        # 使用日期作为文件名的一部分
        date_str = datetime.now().strftime('%Y-%m-%d')
        feedback_file = os.path.join(feedback_dir, f'feedback_{date_str}.jsonl')
        
        # 追加到文件（JSONL格式，每行一个JSON对象）
        with open(feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + '\n')
        
        logger.info(f"收到用户反馈: 类型={feedback_data.get('type')}, 股票={feedback_data.get('ticker', 'N/A')}, IP={request.remote_addr}")
        
        return jsonify({'success': True, 'message': '反馈提交成功'})
    
    except Exception as e:
        logger.error(f"处理反馈时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500


if __name__ == '__main__':
    print("启动投资分析系统...")
    print("服务器地址: http://127.0.0.1:5002")
    print("注意: 端口5000被Apple AirPlay占用，已改用5002端口")
    app.run(debug=True, port=5002, host='0.0.0.0', threaded=True)

