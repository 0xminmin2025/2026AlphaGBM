from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta, time
from flask_cors import CORS
import random
import string
import os
import re
import logging
import json
import pandas as pd
import urllib.parse
import smtplib
from analysis_engine import get_market_data, get_ticker_price, analyze_risk_and_position, calculate_market_sentiment, calculate_target_price, calculate_atr_stop_loss
from ai_service import get_gemini_analysis

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

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("未安装 python-dotenv 模块，无法加载环境变量")

# 尝试导入数据库和JWT相关模块
try:
    from flask_sqlalchemy import SQLAlchemy
except ImportError:
    SQLAlchemy = None
    
try:
    from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
except ImportError:
    JWTManager = None
    create_access_token = None
    jwt_required = lambda: lambda f: f  # 降级为无操作装饰器
    get_jwt_identity = None

try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    def generate_password_hash(password):
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
        
    def check_password_hash(password_hash, password):
        import hashlib
        return password_hash == hashlib.sha256(password.encode()).hexdigest()

try:
    from flask_mail import Mail, Message
except ImportError:
    Mail = None
    Message = None


# 初始化Flask应用
app = Flask(__name__)
# CORS配置
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# 配置数据库和JWT
# MySQL数据库连接配置 - 从环境变量读取
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'alphag_db')

# 对密码进行URL编码，以处理特殊字符
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', '')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.getenv('JWT_EXPIRE_HOURS', '24')))

# 邮件配置 - 从环境变量读取
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))

# 初始化扩展
db = SQLAlchemy(app) if SQLAlchemy else None
jwt = JWTManager(app) if JWTManager else None
mail = Mail(app) if Mail else None

# 如果缺少必要依赖，记录警告
if not SQLAlchemy or not JWTManager:
    logger.warning("缺少依赖库: flask_sqlalchemy 或 flask_jwt_extended")
    logger.warning("认证功能将不可用，请安装所需依赖: pip install -r requirements.txt")
    
if not Mail:
    logger.warning("缺少依赖库: flask_mail")
    logger.warning("邮箱验证码功能将不可用，请安装所需依赖: pip install -r requirements.txt")

# 用户模型
if SQLAlchemy:
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False, index=True)  # 添加索引优化查询性能
        password_hash = db.Column(db.String(200), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.now)
        last_login = db.Column(db.DateTime, nullable=True)
        is_email_verified = db.Column(db.Boolean, default=False)  # 添加邮箱验证状态字段
        
        def set_password(self, password):
            self.password_hash = generate_password_hash(password)
            
        def check_password(self, password):
            return check_password_hash(self.password_hash, password)
    
    # 邮箱验证码模型
    class EmailVerification(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), nullable=False, index=True)
        verification_code = db.Column(db.String(6), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.now)
        expires_at = db.Column(db.DateTime, nullable=False)
        is_used = db.Column(db.Boolean, default=False)
    
    # 分析请求记录表
    class AnalysisRequest(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # 允许匿名用户，添加索引优化查询性能
        ticker = db.Column(db.String(20), nullable=False)
        style = db.Column(db.String(20), nullable=False)
        status = db.Column(db.String(20), nullable=False, default='success')  # success/failed
        error_message = db.Column(db.Text, nullable=True)  # 错误信息（如果有）
        created_at = db.Column(db.DateTime, default=datetime.now)
        
        # 关联到用户表
        user = db.relationship('User', backref=db.backref('analysis_requests', lazy=True))
    
    # 用户反馈模型
    class Feedback(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
        type = db.Column(db.String(50), nullable=False)  # 反馈类型
        content = db.Column(db.Text, nullable=False)  # 反馈内容
        ticker = db.Column(db.String(20), nullable=True)  # 相关股票代码（如果有）
        ip_address = db.Column(db.String(50), nullable=True)  # IP地址
        submitted_at = db.Column(db.DateTime, default=datetime.now)  # 提交时间
        
        # 关联到用户表
        user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
    
    # 每日查询统计模型
    class DailyQueryCount(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)  # 添加索引优化查询性能
        date = db.Column(db.Date, nullable=False)  # 查询日期
        query_count = db.Column(db.Integer, default=0)  # 已使用查询次数
        max_queries = db.Column(db.Integer, default=10)  # 每日最大查询次数（默认10次）
        reset_time = db.Column(db.DateTime, nullable=False)  # 下次重置时间
        
        # 关联到用户表
        user = db.relationship('User', backref=db.backref('daily_queries', lazy=True))

# 辅助函数：从JWT令牌获取用户信息
def get_user_info_from_token():
    """从JWT令牌获取并转换用户ID"""
    try:
        if not JWTManager or not get_jwt_identity:
            return None
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str) if user_id_str else None
        return {'user_id': user_id}
    except Exception:
        return None

def get_or_create_daily_query_count(user_id):
    """获取或创建用户当日的查询统计记录"""
    # 获取当前日期（仅年月日）
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    reset_time = datetime.combine(tomorrow, time.min)
    
    # 查找用户今日的查询记录
    daily_query = DailyQueryCount.query.filter_by(
        user_id=user_id,
        date=today
    ).first()
    
    # 如果今日记录不存在或重置日期已过，则创建新记录或重置
    if not daily_query:
        # 删除可能存在的过期记录
        DailyQueryCount.query.filter_by(user_id=user_id).delete()
        
        # 创建新的每日查询记录
        daily_query = DailyQueryCount(
            user_id=user_id,
            date=today,
            query_count=0,
            max_queries=10,  # 默认每天10次
            reset_time=reset_time
        )
        db.session.add(daily_query)
        db.session.commit()
    elif datetime.now() >= daily_query.reset_time:
        # 如果记录已过期，则重置查询计数
        daily_query.date = today
        daily_query.query_count = 0
        daily_query.reset_time = reset_time
        db.session.commit()
    
    return daily_query

def increment_query_count(user_id):
    """增加用户的查询计数"""
    daily_query = get_or_create_daily_query_count(user_id)
    daily_query.query_count += 1
    db.session.commit()
    return daily_query

def generate_verification_code(length=6):
    """生成指定长度的数字验证码"""
    return ''.join(random.choices(string.digits, k=length))

def send_verification_email(recipient_email, code):
    """使用SMTP发送邮箱验证码"""
    if not Mail or not mail:
        logger.error("邮件服务未初始化，无法发送验证码")
        return False
    
    try:
        # 创建邮件消息对象
        msg = Message(
            'AlphaG 邮箱验证', 
            recipients=[recipient_email],
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        # 设置邮件正文
        msg.body = f'''
您的邮箱验证码是: {code}

请在5分钟内使用此验证码。

如果您没有发起此请求，请忽略此邮件。

--
AlphaG投资分析系统
'''
        mail.send(msg)
        logger.info(f"验证码已通过SMTP发送至 {recipient_email}")
        return True
    except ConnectionRefusedError as e:
        logger.error(f"SMTP连接被拒绝: {e}，请检查SMTP服务器地址和端口配置")
        return False
    except TimeoutError as e:
        logger.error(f"SMTP连接超时: {e}")
        return False
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP认证失败: {e}，请检查邮箱账号和密码配置")
        return False
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP服务器断开连接: {e}")
        return False
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        return False


@app.route('/')
def index():
    return render_template('index.html')

# 用户注册API端点 - 第一步：请求验证码
@app.route('/api/register/request-code', methods=['POST'])
def request_verification_code():
    # 如果缺少必要依赖，返回友好错误
    if not SQLAlchemy or not Mail:
        return jsonify({'error': '验证码模块未启用，请安装所需依赖: pip install -r requirements.txt'}), 503
        
    try:
        data = request.json
        
        # 验证输入参数
        if 'email' not in data:
            return jsonify({'error': '缺少邮箱参数'}), 400
        
        email = data['email'].strip()
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': '邮箱格式不正确'}), 400
        
        # 检查邮箱是否已存在且已验证
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.is_email_verified:
            return jsonify({'error': '该邮箱已被注册并验证'}), 409
        
        # 生成验证码
        code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=5)
        
        # 删除该邮箱之前的验证码
        EmailVerification.query.filter_by(email=email).delete()
        
        # 保存新验证码
        verification = EmailVerification(
            email=email,
            verification_code=code,
            expires_at=expires_at
        )
        db.session.add(verification)
        db.session.commit()
        
        # 发送验证码邮件
        if send_verification_email(email, code):
            return jsonify({
                'message': '验证码已发送至您的邮箱，请查收',
                'email': email
            }), 200
        else:
            return jsonify({'error': '发送验证码失败，请稍后重试'}), 500
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"发送验证码请求失败: {e}")
        return jsonify({'error': '请求处理过程中发生错误'}), 500

# 用户注册API端点 - 第二步：提交验证码和注册信息
@app.route('/api/register', methods=['POST'])
def register():
    # 如果缺少必要依赖，返回友好错误
    if not SQLAlchemy or not JWTManager:
        return jsonify({'error': '认证模块未启用，请安装所需依赖: pip install -r requirements.txt'}), 503
        
    try:
        data = request.json
        
        # 验证输入参数
        required_fields = ['username', 'email', 'password', 'verification_code']
        if not all(k in data for k in required_fields):
            return jsonify({'error': '缺少必要参数，请提供用户名、邮箱、密码和验证码'}), 400
        
        username = data['username'].strip()
        email = data['email'].strip()
        password = data['password']
        code = data['verification_code'].strip()
        
        # 验证用户名格式
        if len(username) < 3 or len(username) > 20:
            return jsonify({'error': '用户名长度必须在3-20个字符之间'}), 400
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': '邮箱格式不正确'}), 400
        
        # 验证密码强度
        if len(password) < 6:
            return jsonify({'error': '密码长度至少为6个字符'}), 400
        
        # 验证验证码
        verification = EmailVerification.query.filter_by(
            email=email,
            verification_code=code,
            is_used=False
        ).first()
        
        if not verification:
            return jsonify({'error': '验证码无效或已过期'}), 400
        
        if datetime.now() > verification.expires_at:
            return jsonify({'error': '验证码已过期，请重新获取'}), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'}), 409
        
        # 标记验证码为已使用
        verification.is_used = True
        
        # 创建或更新用户
        user = User.query.filter_by(email=email).first()
        if user:
            # 如果用户存在但未验证，则更新信息
            user.username = username
            user.set_password(password)
            user.is_email_verified = True
            user.last_login = datetime.now()
        else:
            # 创建新用户
            user = User(username=username, email=email, is_email_verified=True, last_login=datetime.now())
            user.set_password(password)
            db.session.add(user)
        
        db.session.commit()
        
        logger.info(f"新用户注册成功: {username}")
        
        # 创建访问令牌
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': '注册成功',
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'access_token': access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"用户注册失败: {e}")
        return jsonify({'error': '注册过程中发生错误'}), 500

# 用户登录API端点
@app.route('/api/login', methods=['POST'])
def login():
    # 如果缺少必要依赖，返回友好错误
    if not SQLAlchemy or not JWTManager:
        return jsonify({'error': '认证模块未启用，请安装所需依赖: pip install -r requirements.txt'}), 503
        
    try:
        data = request.json
        
        # 验证输入参数
        if not all(k in data for k in ['email', 'password']):
            return jsonify({'error': '缺少必要参数'}), 400
        
        email = data['email'].strip()
        password = data['password']
        
        # 通过邮箱查找用户
        user = User.query.filter_by(email=email).first()
        
        # 验证用户是否存在且密码正确
        if not user or not user.check_password(password):
            return jsonify({'error': '邮箱或密码错误'}), 401
        
        # 检查邮箱是否已验证
        if not user.is_email_verified:
            return jsonify({'error': '邮箱尚未验证，请先验证邮箱'}), 403
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        db.session.commit()
        
        logger.info(f"用户登录成功: {user.username} (ID: {user.id})")
        
        # 创建访问令牌
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': '登录成功',
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'access_token': access_token
        }), 200
        
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        return jsonify({'error': '登录过程中发生错误'}), 500


# 用户忘记密码API端点 - 第一步：请求重置密码验证码
@app.route('/api/forgot-password/request-code', methods=['POST'])
def request_password_reset_code():
    # 如果缺少必要依赖，返回友好错误
    if not SQLAlchemy or not Mail:
        return jsonify({'error': '验证码模块未启用，请安装所需依赖: pip install -r requirements.txt'}), 503
        
    try:
        data = request.json
        
        # 验证输入参数
        if 'email' not in data:
            return jsonify({'error': '缺少邮箱参数'}), 400
        
        email = data['email'].strip()
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': '邮箱格式不正确'}), 400
        
        # 检查邮箱是否已注册
        existing_user = User.query.filter_by(email=email).first()
        if not existing_user:
            return jsonify({'error': '该邮箱未注册，请先注册'}), 404
        
        # 生成验证码
        code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=5)
        
        # 删除该邮箱之前的验证码
        EmailVerification.query.filter_by(email=email).delete()
        
        # 保存新验证码
        verification = EmailVerification(
            email=email,
            verification_code=code,
            expires_at=expires_at
        )
        db.session.add(verification)
        db.session.commit()
        
        # 发送验证码邮件
        if send_verification_email(email, code):
            return jsonify({
                'message': '验证码已发送至您的邮箱，请查收',
                'email': email
            }), 200
        else:
            return jsonify({'error': '发送验证码失败，请稍后重试'}), 500
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"发送密码重置验证码请求失败: {e}")
        return jsonify({'error': '请求处理过程中发生错误'}), 500

# 用户忘记密码API端点 - 第二步：验证验证码并重置密码
@app.route('/api/forgot-password/reset', methods=['POST'])
def reset_password():
    # 如果缺少必要依赖，返回友好错误
    if not SQLAlchemy:
        return jsonify({'error': '认证模块未启用，请安装所需依赖: pip install -r requirements.txt'}), 503
        
    try:
        data = request.json
        
        # 验证输入参数
        required_fields = ['email', 'verification_code', 'new_password']
        if not all(k in data for k in required_fields):
            return jsonify({'error': '缺少必要参数，请提供邮箱、验证码和新密码'}), 400
        
        email = data['email'].strip()
        code = data['verification_code'].strip()
        new_password = data['new_password']
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': '邮箱格式不正确'}), 400
        
        # 验证密码强度
        if len(new_password) < 6:
            return jsonify({'error': '密码长度至少为6个字符'}), 400
        
        # 验证验证码
        verification = EmailVerification.query.filter_by(
            email=email,
            verification_code=code,
            is_used=False
        ).first()
        
        if not verification:
            return jsonify({'error': '验证码无效或已过期'}), 400
        
        if datetime.now() > verification.expires_at:
            return jsonify({'error': '验证码已过期，请重新获取'}), 400
        
        # 查找用户
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        # 标记验证码为已使用
        verification.is_used = True
        
        # 更新用户密码
        user.set_password(new_password)
        
        # 提交更改
        db.session.commit()
        
        logger.info(f"用户密码重置成功: {email}")
        
        return jsonify({
            'message': '密码重置成功，请使用新密码登录'
        }), 200
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"密码重置失败: {e}")
        return jsonify({'error': '密码重置过程中发生错误'}), 500


# 查询次数限制相关辅助函数
@app.route('/api/query_count', methods=['GET'])
@jwt_required()
def get_query_count():
    """获取用户每日查询次数信息"""
    # 获取用户信息
    user_info = get_user_info_from_token()
    if not user_info or 'user_id' not in user_info:
        return jsonify({'error': '未授权访问'}), 401
    
    user_id = user_info['user_id']
    
    # 获取或创建每日查询次数记录
    daily_query = get_or_create_daily_query_count(user_id)
    
    # 返回查询次数信息
    return jsonify({
        'used': daily_query.query_count,
        'max': daily_query.max_queries,
        'reset_time': daily_query.reset_time.strftime('%Y-%m-%d %H:%M:%S') if daily_query.reset_time else None
    })

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
@jwt_required()
def analyze():
    # 获取用户信息
    user_info = get_user_info_from_token()
    if not user_info or 'user_id' not in user_info or not user_info['user_id']:
        return jsonify({'success': False, 'error': '请先登录后再进行分析'}), 401
    current_user_id = user_info['user_id']
    
    # 检查查询次数限制
    daily_query = get_or_create_daily_query_count(current_user_id)
    if daily_query.query_count >= daily_query.max_queries:
        return jsonify({
            'success': False, 
            'error': '查询次数已达上限',
            'query_info': {
                'used': daily_query.query_count,
                'max': daily_query.max_queries,
                'reset_time': daily_query.reset_time.strftime('%Y-%m-%d %H:%M:%S') if daily_query.reset_time else None
            }
        }), 429  # 429 Too Many Requests
    
    # 创建分析请求记录
    analysis_request = AnalysisRequest()
    
    try:
        req_data = request.json
        ticker = req_data.get('ticker', '').upper()
        style = req_data.get('style', 'quality')
        onlyHistoryData = req_data.get('onlyHistoryData', False)
        startDate = req_data.get('startDate', None)
        
        # 更新分析请求记录
        analysis_request.ticker = ticker
        analysis_request.style = style
        
        # 设置用户ID
        analysis_request.user_id = current_user_id
        user = User.query.get(current_user_id) if current_user_id else None
        logger.info(f"收到分析请求: {ticker}, 风格: {style}, onlyHistoryData: {onlyHistoryData}, 用户: {user.username if user else '未知'}, 用户ID: {current_user_id}")

        # 增加查询计数
        daily_query = increment_query_count(current_user_id)

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
            
            # 更新错误状态
            analysis_request.status = 'failed'
            analysis_request.error_message = error_msg
            db.session.add(analysis_request)
            db.session.commit()
            
            return jsonify({'success': False, 'error': error_msg}), 400
        
        if not market_data:
            error_msg = f'找不到股票代码 "{ticker}" 或数据获取失败'
            if normalized_ticker != ticker:
                error_msg += f'\n已尝试标准化为: {normalized_ticker}'
            error_msg += '\n\n可能的原因：\n1. 股票代码不存在\n2. 网络连接问题\n3. 数据源暂时不可用\n\n请尝试：\n- 港股代码：2525 或 2525.HK\n- 美股代码：AAPL\n- A股代码：600519'
            
            # 更新错误状态
            analysis_request.status = 'failed'
            analysis_request.error_message = error_msg
            db.session.add(analysis_request)
            db.session.commit()
            
            return jsonify({'success': False, 'error': error_msg}), 400

        if onlyHistoryData:
            # 准备返回数据
            response_data = {'success': True, 'data': market_data}
            
            # 保存结果到数据库
            db.session.add(analysis_request)
            db.session.commit()
            
            return jsonify(response_data)


        # 2. 计算硬逻辑
        try:
            risk_result = analyze_risk_and_position(style, market_data)
        except Exception as e:
            print(f"计算风险评分时发生异常: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f'风险计算失败: {str(e)}'
            
            # 更新错误状态
            analysis_request.status = 'failed'
            analysis_request.error_message = error_msg
            db.session.add(analysis_request)
            db.session.commit()
            
            return jsonify({'success': False, 'error': error_msg}), 500
        
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
        
        # 准备返回数据
        response_data = {
            'success': True,
            'data': serializable_data,
            'risk': serializable_risk,
            'report': ai_report,
            'query_info': {
                'used': daily_query.query_count,
                'max': daily_query.max_queries,
                'reset_time': daily_query.reset_time.strftime('%Y-%m-%d %H:%M:%S') if daily_query.reset_time else None
            }
        }
        
        # 保存结果到数据库
        db.session.add(analysis_request)
        db.session.commit()
        
        return jsonify(response_data)
    
    except Exception as e:
        # 捕获所有其他异常
        import traceback
        traceback.print_exc()
        error_msg = f'分析过程中发生错误: {str(e)}'
        
        # 更新错误状态
        analysis_request.status = 'failed'
        analysis_request.error_message = error_msg
        
        try:
            db.session.add(analysis_request)
            db.session.commit()
        except Exception as db_error:
            logger.error(f"保存分析请求记录时出错: {db_error}")
        
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """接收用户反馈"""
    try:
        # 获取用户信息
        user_info = get_user_info_from_token()
        if not user_info or 'user_id' not in user_info:
            return jsonify({'success': False, 'error': '请先登录后再提交反馈'}), 401
        user_id = user_info['user_id']
        
        feedback_data = request.json
        
        # 验证必填字段
        if not feedback_data.get('type'):
            return jsonify({'success': False, 'error': '请选择反馈类型'}), 400
        
        if not feedback_data.get('content'):
            return jsonify({'success': False, 'error': '请填写反馈内容'}), 400
        
        # 创建反馈记录
        feedback = Feedback(
            user_id=user_id,
            type=feedback_data.get('type'),
            content=feedback_data.get('content'),
            ticker=feedback_data.get('ticker'),
            # 优先从反向代理头获取真实外网IP，回退到容器内IP
            ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or \
                         request.headers.get('X-Real-IP') or \
                         request.remote_addr
        )
        
        # 保存到数据库
        db.session.add(feedback)
        db.session.commit()
        
        logger.info(f"收到用户反馈: 用户ID={user_id}, 类型={feedback_data.get('type')}, 股票={feedback_data.get('ticker', 'N/A')}")
        
        return jsonify({'success': True, 'message': '反馈提交成功'})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"处理反馈时出错: {str(e)}")
        return jsonify({'success': False, 'error': f"服务器错误: {str(e)}"}), 500


if __name__ == '__main__':
    print("启动投资分析系统...")
    # 确保数据库表存在
    with app.app_context():
        db.create_all()
    print("服务器地址: http://127.0.0.1:5002")
    app.run(debug=True, port=5002, host='0.0.0.0', threaded=True)
