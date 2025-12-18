from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from flask_cors import CORS
import pandas as pd
import logging
import os
import json
import hashlib
import secrets
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

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

# 认证相关配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'alphag-secret-key-change-in-production')

# 用户数据文件路径
USERS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
TOKENS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'tokens.json')
VERIFICATION_CODES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'verification_codes.json')

# 确保数据目录存在
os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

def load_users():
    """加载用户数据"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    """保存用户数据"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_tokens():
    """加载token数据"""
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tokens(tokens):
    """保存token数据"""
    # 清理过期的token（超过7天）
    now = datetime.now().isoformat()
    tokens = {k: v for k, v in tokens.items() if v.get('expires_at', '') > now}
    
    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """验证密码"""
    return hash_password(password) == password_hash

def generate_token():
    """生成随机token"""
    return secrets.token_urlsafe(32)

def load_verification_codes():
    """加载验证码数据"""
    if os.path.exists(VERIFICATION_CODES_FILE):
        try:
            with open(VERIFICATION_CODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_verification_codes(codes):
    """保存验证码数据"""
    # 清理过期的验证码（超过10分钟）
    now = datetime.now().isoformat()
    codes = {k: v for k, v in codes.items() if v.get('expires_at', '') > now}
    
    with open(VERIFICATION_CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)

def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def send_verification_email(email, code):
    """发送验证码邮件"""
    try:
        # 从环境变量读取SMTP配置（如果未配置，使用测试模式）
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        smtp_from = os.getenv('SMTP_FROM', smtp_user)
        
        # 如果没有配置SMTP，打印验证码到日志（用于开发和测试）
        if not smtp_user or not smtp_password:
            logger.warning(f"SMTP未配置，验证码将打印到日志（仅用于开发测试）")
            logger.info(f"用户 {email} 的验证码: {code}")
            return True
        
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'AlphaG股票分析系统 - 密码重置验证码'
        msg['From'] = smtp_from
        msg['To'] = email
        
        # 邮件正文（HTML格式）
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3b82f6;">AlphaG股票分析系统</h2>
                <p>您好，</p>
                <p>您正在尝试重置密码，请使用以下验证码：</p>
                <div style="background: #f3f4f6; border: 2px solid #3b82f6; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #3b82f6; font-size: 32px; margin: 0; letter-spacing: 5px;">{code}</h1>
                </div>
                <p>验证码有效期为 <strong>10分钟</strong>。</p>
                <p style="color: #64748b; font-size: 12px; margin-top: 30px;">
                    如果您没有申请密码重置，请忽略此邮件。
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        AlphaG股票分析系统 - 密码重置验证码
        
        您的验证码是: {code}
        
        验证码有效期为 10分钟。
        
        如果您没有申请密码重置，请忽略此邮件。
        """
        
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # 发送邮件
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"验证码邮件已发送到: {email}")
        return True
        
    except Exception as e:
        logger.error(f"发送验证码邮件失败: {e}")
        # 如果发送失败，在开发模式下打印到日志
        logger.warning(f"邮件发送失败，验证码: {code} (仅用于开发测试)")
        return False

def init_test_user():
    """初始化测试账号"""
    users = load_users()
    
    # 创建测试账号（如果不存在）
    test_email = 'test@alphag.com'
    if test_email not in users:
        users[test_email] = {
            'username': 'testuser',
            'email': test_email,
            'password_hash': hash_password('test123456'),  # 测试密码：test123456
            'created_at': datetime.now().isoformat()
        }
        save_users(users)
        logger.info(f"已创建测试账号: {test_email} / test123456")
    
    return users

@app.route('/')
def index():
    # 初始化测试账号
    init_test_user()
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
        error_msg = str(e)
        
        # 检查是否是速率限制错误或数据源繁忙错误
        if "数据源暂时繁忙" in error_msg or "速率限制" in error_msg or "Too Many Requests" in error_msg or "Rate limited" in error_msg:
            # 如果错误信息已经包含了详细说明，直接使用
            if "数据源暂时繁忙" in error_msg or "⚠️" in error_msg:
                pass  # 使用原始错误消息
            else:
                error_msg = f'⚠️ 数据源暂时繁忙\n\n当前请求过于频繁，请稍候 10-30 秒后重试。\n\n建议：\n- 等待 30 秒后再试\n- 避免短时间内多次查询\n- 如果持续出现此问题，可能是数据源临时维护'
        else:
            # 如果错误信息已经包含了详细信息，直接使用；否则添加前缀
            if "数据获取失败" not in error_msg and "无法获取股票" not in error_msg:
                error_msg = f'数据获取失败: {error_msg}'
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
        
        # 根据目标价格和当前价格的关系，调整仓位建议
        current_price = market_data.get('price', 0)
        if target_price and current_price > 0:
            price_ratio = current_price / target_price
            original_position = risk_result['suggested_position']
            
            # 如果当前价格已经超过目标价格，降低仓位建议
            if price_ratio >= 1.2:  # 超过目标价格20%以上
                risk_result['suggested_position'] = max(0, original_position * 0.2)
                risk_result['flags'].append(f"价格过高: 当前价格超过目标价格{((price_ratio-1)*100):.1f}%，建议观望或减仓")
            elif price_ratio >= 1.1:  # 超过目标价格10-20%
                risk_result['suggested_position'] = max(0, original_position * 0.4)
                risk_result['flags'].append(f"价格偏高: 当前价格超过目标价格{((price_ratio-1)*100):.1f}%，建议谨慎")
            elif price_ratio >= 1.0:  # 达到或略超目标价格（0-10%）
                risk_result['suggested_position'] = max(0, original_position * 0.5)
                risk_result['flags'].append(f"价格已达目标: 当前价格达到目标价格，建议考虑止盈")
            elif price_ratio >= 0.95:  # 接近目标价格（95-100%）
                risk_result['suggested_position'] = original_position * 0.8
            elif price_ratio >= 0.9:  # 接近目标价格（90-95%）
                risk_result['suggested_position'] = original_position * 0.9
            
            # 确保仓位是合理的数值（保留1位小数）
            risk_result['suggested_position'] = round(risk_result['suggested_position'], 1)
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


@app.route('/api/register', methods=['POST'])
def register():
    """用户注册（简化版，无需验证码）"""
    try:
        data = request.json
        
        # 验证必填字段
        required_fields = ['username', 'email', 'password']
        if not all(k in data for k in required_fields):
            return jsonify({'success': False, 'error': '请提供用户名、邮箱和密码'}), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # 验证用户名格式
        if len(username) < 3 or len(username) > 20:
            return jsonify({'success': False, 'error': '用户名长度必须在3-20个字符之间'}), 400
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': '邮箱格式不正确'}), 400
        
        # 验证密码长度
        if len(password) < 6:
            return jsonify({'success': False, 'error': '密码长度至少为6个字符'}), 400
        
        # 检查用户是否已存在
        users = load_users()
        if email in users:
            return jsonify({'success': False, 'error': '该邮箱已被注册'}), 409
        
        # 创建新用户
        users[email] = {
            'username': username,
            'email': email,
            'password_hash': hash_password(password),
            'created_at': datetime.now().isoformat()
        }
        save_users(users)
        
        logger.info(f"新用户注册成功: {username} ({email})")
        
        # 生成token
        token = generate_token()
        tokens = load_tokens()
        tokens[token] = {
            'user_id': email,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        }
        save_tokens(tokens)
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'access_token': token,
            'username': username,
            'email': email
        }), 201
        
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        return jsonify({'success': False, 'error': f'注册失败: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        
        # 验证必填字段
        if not all(k in data for k in ['email', 'password']):
            return jsonify({'success': False, 'error': '请提供邮箱和密码'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        
        # 加载用户数据
        users = load_users()
        
        # 验证用户是否存在
        if email not in users:
            return jsonify({'success': False, 'error': '邮箱或密码错误'}), 401
        
        user = users[email]
        
        # 验证密码
        if not verify_password(password, user['password_hash']):
            return jsonify({'success': False, 'error': '邮箱或密码错误'}), 401
        
        # 生成token
        token = generate_token()
        tokens = load_tokens()
        tokens[token] = {
            'user_id': email,
            'username': user['username'],
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        }
        save_tokens(tokens)
        
        logger.info(f"用户登录成功: {user['username']} ({email})")
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'access_token': token,
            'username': user['username'],
            'email': email
        }), 200
        
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        return jsonify({'success': False, 'error': f'登录失败: {str(e)}'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if token:
            tokens = load_tokens()
            if token in tokens:
                del tokens[token]
                save_tokens(tokens)
                logger.info(f"用户登出: token已删除")
        
        return jsonify({'success': True, 'message': '登出成功'}), 200
        
    except Exception as e:
        logger.error(f"登出失败: {e}")
        return jsonify({'success': False, 'error': f'登出失败: {str(e)}'}), 500

def verify_token(token):
    """验证token并返回用户信息"""
    if not token:
        return None
    
    tokens = load_tokens()
    if token not in tokens:
        return None
    
    token_data = tokens[token]
    
    # 检查token是否过期
    if datetime.now().isoformat() > token_data.get('expires_at', ''):
        # 删除过期token
        del tokens[token]
        save_tokens(tokens)
        return None
    
    return token_data

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

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """发送密码重置验证码"""
    try:
        data = request.json
        
        if not data or 'email' not in data:
            return jsonify({'success': False, 'error': '请提供邮箱地址'}), 400
        
        email = data['email'].strip().lower()
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': '邮箱格式不正确'}), 400
        
        # 检查用户是否存在
        users = load_users()
        if email not in users:
            # 为了安全，不告知用户邮箱是否存在
            return jsonify({
                'success': True,
                'message': '如果该邮箱已注册，验证码已发送到您的邮箱'
            }), 200
        
        # 生成验证码
        code = generate_verification_code()
        
        # 保存验证码（有效期10分钟）
        codes = load_verification_codes()
        codes[email] = {
            'code': code,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=10)).isoformat()
        }
        save_verification_codes(codes)
        
        # 发送邮件
        send_verification_email(email, code)
        
        logger.info(f"密码重置验证码已发送到: {email}")
        
        return jsonify({
            'success': True,
            'message': '验证码已发送到您的邮箱，请查收（有效期10分钟）'
        }), 200
        
    except Exception as e:
        logger.error(f"发送密码重置验证码失败: {e}")
        return jsonify({'success': False, 'error': f'发送失败: {str(e)}'}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """重置密码（验证验证码并设置新密码）"""
    try:
        data = request.json
        
        required_fields = ['email', 'code', 'new_password']
        if not all(k in data for k in required_fields):
            return jsonify({'success': False, 'error': '请提供邮箱、验证码和新密码'}), 400
        
        email = data['email'].strip().lower()
        code = data['code'].strip()
        new_password = data['new_password']
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': '邮箱格式不正确'}), 400
        
        # 验证密码长度
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': '密码长度至少为6个字符'}), 400
        
        # 验证验证码
        codes = load_verification_codes()
        if email not in codes:
            return jsonify({'success': False, 'error': '验证码无效或已过期'}), 400
        
        code_data = codes[email]
        
        # 检查验证码是否过期
        expires_at = datetime.fromisoformat(code_data['expires_at'])
        if datetime.now() > expires_at:
            # 删除过期验证码
            del codes[email]
            save_verification_codes(codes)
            return jsonify({'success': False, 'error': '验证码已过期，请重新获取'}), 400
        
        # 验证验证码是否正确
        if code_data['code'] != code:
            return jsonify({'success': False, 'error': '验证码错误'}), 400
        
        # 检查用户是否存在
        users = load_users()
        if email not in users:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        # 更新密码
        users[email]['password_hash'] = hash_password(new_password)
        save_users(users)
        
        # 删除已使用的验证码
        del codes[email]
        save_verification_codes(codes)
        
        logger.info(f"用户 {email} 成功重置密码")
        
        return jsonify({
            'success': True,
            'message': '密码重置成功，请使用新密码登录'
        }), 200
        
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'重置失败: {str(e)}'}), 500


if __name__ == '__main__':
    print("启动投资分析系统...")
    print("服务器地址: http://127.0.0.1:5002")
    print("注意: 端口5000被Apple AirPlay占用，已改用5002端口")
    app.run(debug=True, port=5002, host='0.0.0.0', threaded=True)

