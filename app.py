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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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

# 初始化定时任务调度器
scheduler = BackgroundScheduler()

# 配置数据库和JWT
# 临时使用 SQLite 进行测试（方便开发）
# 生产环境请使用 MySQL
USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'

if USE_SQLITE:
    # SQLite 配置
    db_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(db_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(db_dir, "alphag.db")}'
    logger.info("使用 SQLite 数据库")
else:
    # MySQL数据库连接配置 - 从环境变量读取
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'alphag_db')
    
    # 对密码进行URL编码，以处理特殊字符
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    logger.info(f"使用 MySQL 数据库: {DB_NAME}")

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

# 普通用户每日最大查询次数
REGULAR_USER_DAILY_MAX_QUERIES = int(os.getenv('REGULAR_USER_DAILY_MAX_QUERIES', '5'))

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
        max_queries = db.Column(db.Integer, default=5)  # 每日最大查询次数（默认5次）
        reset_time = db.Column(db.DateTime, nullable=False)  # 下次重置时间
        
        # 关联到用户表
        user = db.relationship('User', backref=db.backref('daily_queries', lazy=True))
    
    # 股票持仓模型
    class PortfolioHolding(db.Model):
        __tablename__ = 'portfolio_holdings'
        
        id = db.Column(db.Integer, primary_key=True)
        ticker = db.Column(db.String(20), nullable=False, index=True)  # 股票代码
        name = db.Column(db.String(100), nullable=False)  # 股票名称
        shares = db.Column(db.Integer, nullable=False)  # 持仓数量
        buy_price = db.Column(db.Float, nullable=False)  # 买入价格
        style = db.Column(db.String(20), nullable=False, index=True)  # 投资风格(quality, value, growth, momentum)
        currency = db.Column(db.String(3), nullable=False)  # 货币单位
        created_at = db.Column(db.DateTime, default=datetime.now)
        updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
        
    # 每日盈亏记录模型
    class DailyProfitLoss(db.Model):
        __tablename__ = 'daily_profit_loss'
        
        id = db.Column(db.Integer, primary_key=True)
        trading_date = db.Column(db.Date, nullable=False, index=True)  # 交易日期
        total_actual_investment = db.Column(db.Float, nullable=False)  # 总实际投入
        total_market_value = db.Column(db.Float, nullable=False)  # 总市值
        total_profit_loss = db.Column(db.Float, nullable=False)  # 总盈亏金额
        total_profit_loss_percent = db.Column(db.Float, nullable=False)  # 总盈亏比例
        created_at = db.Column(db.DateTime, default=datetime.now)

    # 投资风格盈亏记录模型
    class StyleProfit(db.Model):
        __tablename__ = 'style_profits'
        
        id = db.Column(db.Integer, primary_key=True)
        trading_date = db.Column(db.Date, nullable=False, index=True)  # 交易日期
        style = db.Column(db.String(20), nullable=False)  # 投资风格
        style_investment = db.Column(db.Float, nullable=False)  # 该风格的总投资
        style_market_value = db.Column(db.Float, nullable=False)  # 该风格的总市值
        style_profit_loss = db.Column(db.Float, nullable=False)  # 该风格的总盈亏
        style_profit_loss_percent = db.Column(db.Float, nullable=False)  # 该风格的总盈亏比例

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

# 特定用户ID的每日最大查询次数配置
# 格式: USER_<USER_ID>_MAX_QUERIES=次数
# 例如: USER_1_MAX_QUERIES=20
# 如果未设置特定用户ID的查询次数，则使用REGULAR_USER_DAILY_MAX_QUERIES
def get_user_max_queries(user_id):
    """根据用户ID获取其每日最大查询次数"""
    env_key = f'USER_{user_id}_MAX_QUERIES'
    # 先尝试获取特定用户的配置
    if os.getenv(env_key):
        return int(os.getenv(env_key))
    # 其他用户使用普通用户配置
    else:
        return REGULAR_USER_DAILY_MAX_QUERIES

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
        
        # 获取用户的最大查询次数
        dailyMaxQueryCount = get_user_max_queries(user_id)
        
        # 创建新的每日查询记录
        daily_query = DailyQueryCount(
            user_id=user_id,
            date=today,
            query_count=0,
            max_queries=dailyMaxQueryCount,
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


# 自定义异常类
class PortfolioException(Exception):
    """
    投资组合相关自定义异常
    """
    def __init__(self, message, error_code=None, status_code=500):
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.status_code = status_code
        super().__init__(self.message)

def calculate_daily_profit_loss():
    """
    计算每日盈亏金额和盈亏率，并保存到数据库
    
    Returns:
        dict: 包含计算结果的字典，如果数据已存在则返回None
    """
    try:
        with app.app_context():
            # 获取当前日期，使用交易日日期
            today = datetime.now().date()
            
            # 检查今天是否已经计算过盈亏
            existing_record = DailyProfitLoss.query.filter_by(
                trading_date=today
            ).first()
            
            if existing_record:
                logging.info(f"今天 {today} 的盈亏数据已存在，跳过计算")
                return {
                    'total_profit_loss': existing_record.total_profit_loss,
                    'total_profit_loss_percent': existing_record.total_profit_loss_percent,
                    'style_profits': {},
                    'trading_date': today.isoformat()
                }
            
            # 查询所有持仓记录
            holdings = PortfolioHolding.query.all()
            
            if not holdings:
                logging.warning(f"{today}: 没有找到持仓数据，无法计算盈亏")
                raise PortfolioException(
                    message="没有找到持仓数据，无法计算盈亏",
                    error_code="NO_HOLDINGS_DATA",
                    status_code=404
                )
            
            # 计算总体盈亏
            total_investment = 0
            total_market_value = 0
            
            # 汇率定义，用于将不同货币转换为美元
            exchange_rates = {
                'USD': 1.0,
                'HKD': 0.128,  # 港币兑美元汇率
                'CNY': 0.139   # 人民币兑美元汇率
            }
            
            # 按风格分组计算盈亏
            style_data = {}
            for holding in holdings:
                # 获取当前持仓的货币单位
                currency = holding.currency
                # 获取对应的汇率，如果没有定义则使用1.0
                rate = exchange_rates.get(currency, 1.0)
                
                # 将实际投资金额和市值转换为美元
                investment_in_usd = holding.shares * holding.buy_price * rate
                price = get_ticker_price(holding.ticker)
                if price is None:
                    logging.error(f"获取股票 {holding.ticker} 价格失败")
                    raise PortfolioException(
                        message=f"获取股票 {holding.ticker} 价格失败",
                        error_code="PRICE_FETCH_FAILED",
                        status_code=400
                    )
                market_value_in_usd = holding.shares * price * rate
                
                # 使用转换后的美元金额累加
                total_investment += investment_in_usd
                total_market_value += market_value_in_usd
                
                # 更新风格数据
                if holding.style not in style_data:
                    style_data[holding.style] = {
                        'investment': 0,
                        'market_value': 0,
                        'profit_loss': 0
                    }
                
                style_data[holding.style]['investment'] += investment_in_usd
                style_data[holding.style]['market_value'] += market_value_in_usd
            
            # 计算总体盈亏金额和盈亏率
            total_profit_loss = total_market_value - total_investment
            total_profit_loss_percent = (total_profit_loss / total_investment * 100) if total_investment > 0 else 0
            
            # 创建每日盈亏记录
            try:
                # 创建每日盈亏总记录
                daily_profit = DailyProfitLoss(
                    trading_date=today,
                    total_actual_investment=total_investment,
                    total_market_value=total_market_value,
                    total_profit_loss=total_profit_loss,
                    total_profit_loss_percent=total_profit_loss_percent
                )
                db.session.add(daily_profit)
                
                # 创建各风格盈亏记录
                style_profits_data = {}
                for style, data in style_data.items():
                    style_profit_loss = data['market_value'] - data['investment']
                    style_profit_loss_percent = (style_profit_loss / data['investment'] * 100) if data['investment'] > 0 else 0
                    
                    # 保存风格盈亏记录
                    style_profit = StyleProfit(
                        trading_date=today,
                        style=style,
                        style_investment=data['investment'],
                        style_market_value=data['market_value'],
                        style_profit_loss=style_profit_loss,
                        style_profit_loss_percent=style_profit_loss_percent
                    )
                    db.session.add(style_profit)
                    db.session.commit()
                    
                    # 构建返回数据
                    style_profits_data[style] = {
                        'profit_loss': style_profit_loss,
                        'profit_loss_percent': style_profit_loss_percent
                    }
                
                logging.info(f"成功保存 {today} 的盈亏数据: 盈亏金额={total_profit_loss:.2f}, 盈亏率={total_profit_loss_percent:.2f}%")
                
                return {
                    'total_profit_loss': total_profit_loss,
                    'total_profit_loss_percent': total_profit_loss_percent,
                    'style_profits': style_profits_data,
                    'trading_date': today.isoformat()
                }
            
            except Exception as db_error:
                db.session.rollback()
                logging.error(f"保存盈亏数据到数据库时发生错误: {str(db_error)}")
                raise PortfolioException(
                    message=f"保存盈亏数据失败: {str(db_error)}",
                    error_code="DB_SAVE_ERROR",
                    status_code=500
                )
            
    except PortfolioException:
        # 直接重新抛出已定义的自定义异常
        raise
    except Exception as e:
        # 包装其他异常
        raise PortfolioException(
            message=f"计算盈亏过程中发生错误: {str(e)}",
            error_code="CALCULATION_ERROR",
            status_code=500
        )

# 定时任务：每天下午6点执行盈亏计算
def schedule_daily_profit_loss_calculation():
    """
    配置定时任务，每天下午6点自动计算盈亏
    """
    # 每天下午6点执行
    scheduler.add_job(
        func=calculate_daily_profit_loss,
        trigger=CronTrigger(hour=18, minute=0, second=0),
        id='daily_profit_loss_calculation',
        name='每日盈亏自动计算',
        replace_existing=True
    )
    
    # 启动调度器
    scheduler.start()
    logging.info("定时任务调度器已启动，设置每天下午6点自动计算盈亏")

def initialize_app():
    """
    初始化应用配置，包括数据库和定时任务
    """
    try:
        # 创建数据库表
        with app.app_context():
            db.create_all()
            logging.info("数据库表创建成功")
            
            # 启动定时任务
            schedule_daily_profit_loss_calculation()  
    except Exception as e:
        logging.error(f"应用初始化失败: {str(e)}")
        raise


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/demo')
def demo():
    """设计系统演示页面"""
    return render_template('demo.html')

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

@app.route('/api/portfolio/holdings', methods=['GET'])
def get_portfolio_holdings():
    """
    获取投资组合持仓数据
    """
    try:
        # 查询所有持仓记录
        holdings = PortfolioHolding.query.all()
        
        if not holdings:
            # 如果没有持仓数据，返回空列表而不是错误
            logging.info("当前没有持仓数据记录")
            return jsonify({
                'portfolio': {
                    'totalActualInvestment': 0,
                    'totalMarketValue': 0,
                    'totalProfitLoss': 0,
                    'totalProfitLossPercent': '0',
                    'stocks': [],
                    'styleStats': {}
                }
            }), 200
        
        # 转换为前端需要的格式
        stocks_data = []
        total_actual_investment = 0
        total_market_value = 0
        
        # 初始化按风格分组的数据
        style_investments = {}
        style_market_values = {}

        # 汇率定义，用于将不同货币转换为美元
        exchange_rates = {
            'USD': 1.0,
            'HKD': 0.128,  # 港币兑美元汇率
            'CNY': 0.139   # 人民币兑美元汇率
        }
        
        for holding in holdings:
            try:
                price = get_ticker_price(holding.ticker)
                if price is None:
                    return jsonify({'success': False, 'error': f'获取股票 {holding.ticker} 价格失败'}), 400
                
                # 获取当前持仓的货币单位
                currency = getattr(holding, 'currency', 'USD')
                # 获取对应的汇率，如果没有定义则使用1.0
                rate = exchange_rates.get(currency, 1.0)
                
                actualInvestment = holding.shares * holding.buy_price * rate
                marketValue = price * holding.shares * rate
                stocks_data.append({
                    'ticker': holding.ticker,
                    'name': holding.name,
                    'shares': holding.shares,
                    'buyPrice': holding.buy_price,
                    'currency': currency,
                    'actualInvestment': actualInvestment,
                    'finalPrice': price,
                    'marketValue': marketValue,
                    'profitLoss': marketValue - actualInvestment,
                    'profitLossPercent': str(round(marketValue / actualInvestment * 100 - 100, 2)),
                    'style': holding.style
                })
                
                total_actual_investment += actualInvestment
                total_market_value += marketValue
                
                # 按风格分组累计
                if holding.style not in style_investments:
                    style_investments[holding.style] = 0
                    style_market_values[holding.style] = 0
                
                style_investments[holding.style] += actualInvestment
                style_market_values[holding.style] += marketValue
            except Exception as e:
                # 单个持仓数据处理失败，记录日志但继续处理其他数据
                logging.error(f"处理持仓数据时出错: {holding.ticker}, 错误: {str(e)}")
        
        # 计算总体盈亏
        total_profit_loss = total_market_value - total_actual_investment
        total_profit_loss_percent = (total_profit_loss / total_actual_investment * 100) if total_actual_investment > 0 else 0
        
        # 计算各风格的盈亏率
        style_stats = {}
        for style, investment in style_investments.items():
            market_value = style_market_values[style]
            profit_loss = market_value - investment
            profit_loss_percent = (profit_loss / investment * 100) if investment > 0 else 0
            
            # 从StyleProfit中获取昨日数据以计算相对昨日的盈亏率
            try:
                # 获取今日和昨日的记录
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)
                
                # 获取昨日记录
                yesterday_profit = StyleProfit.query.filter_by(
                    style=style,
                    trading_date=yesterday
                ).first()
                
                # 获取今日记录
                today_profit = StyleProfit.query.filter_by(
                    style=style,
                    trading_date=today
                ).first()
                
                # 计算相对昨日的盈亏率
                if yesterday_profit and today_profit:
                    vs_yesterday_percent = (today_profit.style_market_value - yesterday_profit.style_market_value) / yesterday_profit.style_market_value * 100 if yesterday_profit.style_market_value > 0 else 0
                else:
                    vs_yesterday_percent = 0
            except Exception as e:
                logging.error(f"获取风格 {style} 盈亏历史数据时出错: {str(e)}")
                vs_yesterday_percent = 0
            
            style_stats[style] = {
                'actualInvestment': investment,
                'marketValue': market_value,
                'profitLoss': profit_loss,
                'profitLossPercent': str(round(profit_loss_percent, 2)),
                'vsYesterdayPercent': str(vs_yesterday_percent)
            }
        
        # 构建返回数据
        response_data = {
            'success': True,
            'portfolio': {
                'totalActualInvestment': total_actual_investment,
                'totalMarketValue': total_market_value,
                'totalProfitLoss': total_profit_loss,
                'totalProfitLossPercent': str(round(total_profit_loss_percent, 2)),
                'stocks': stocks_data,
                'styleStats': style_stats
            }
        }
        
        logging.info(f"成功获取了 {len(stocks_data)} 条持仓记录")
        return jsonify(response_data), 200
    
    except Exception as e:
        raise PortfolioException(
            message=f"获取持仓数据失败: {str(e)}",
            error_code="GET_HOLDINGS_ERROR",
            status_code=500
        )

@app.route('/api/profit-loss/history', methods=['GET'])
def get_profit_loss_history():
    """
    获取盈亏历史记录
    """
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 30, type=int)
        
        # 限制每页最大记录数
        if per_page > 100:
            per_page = 100
        
        # 查询每日盈亏记录，按日期倒序排列
        pagination = DailyProfitLoss.query.order_by(
            DailyProfitLoss.trading_date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        daily_records = pagination.items
        
        # 转换为前端需要的格式
        history_data = []
        for record in daily_records:
            # 查询该日期的风格盈亏记录
            style_profits = StyleProfit.query.filter_by(
                trading_date=record.trading_date
            ).all()
            
            # 构建风格盈亏数据
            style_data = {
                style_profit.style: {
                    'profit_loss': style_profit.style_profit_loss,
                    'profit_loss_percent': style_profit.style_profit_loss_percent
                }
                for style_profit in style_profits
            }
            
            history_data.append({
                'date': record.trading_date.isoformat(),
                'total_profit_loss': record.total_profit_loss,
                'total_profit_loss_percent': record.total_profit_loss_percent,
                'total_investment': record.total_actual_investment,
                'total_market_value': record.total_market_value,
                'style_profits': style_data
            })
        
        # 返回分页数据
        return jsonify({
            "success": True,
            "data": {
                "items": history_data,
                "total": pagination.total,
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page
            }
        }), 200
    except Exception as e:
        raise PortfolioException(
            message=f"获取盈亏历史记录失败: {str(e)}",
            error_code="GET_HISTORY_ERROR",
            status_code=500
        )


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
        
        # 4.6. 计算 EV（期望值）模型
        try:
            from ev_model import calculate_ev_model
            ev_result = calculate_ev_model(market_data, risk_result, style)
            market_data['ev_model'] = ev_result
            logger.info(f"EV模型计算完成: {ticker}, 加权EV={ev_result.get('ev_weighted_pct', 0):.2f}%")
        except Exception as e:
            print(f"计算EV模型时发生异常: {e}")
            import traceback
            traceback.print_exc()
            # 使用默认值
            market_data['ev_model'] = {
                'error': str(e),
                'ev_weighted': 0.0,
                'ev_weighted_pct': 0.0,
                'ev_score': 5.0,
                'recommendation': {
                    'action': 'HOLD',
                    'reason': 'EV模型计算失败',
                    'confidence': 'low'
                }
            }

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
    print("服务器地址: http://127.0.0.1:5002")
    # 初始化应用配置和定时任务
    initialize_app()
    app.run(debug=False, port=5002, host='0.0.0.0', threaded=True)
