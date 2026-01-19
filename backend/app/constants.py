"""
系统配置参数
将所有硬编码的"魔法数字"提取到配置文件，便于后续调优和维护
"""

# ==================== 估值参数 ====================

# 增长率折现系数（growth_multiplier中的系数）
GROWTH_DISCOUNT_FACTOR = 0.6  # 给予60%的增长溢价

# 技术面分析系数
TECHNICAL_SENTIMENT_BOOST = 0.10  # 技术情绪分数加成（10%）

# 价格位置阈值
PRICE_POSITION_LOW = 0.3   # 价格在52周区间的前30%视为低位
PRICE_POSITION_MID = 0.7   # 价格在52周区间的前70%视为中位

# PEG阈值（基础值，会根据美债收益率动态调整）
PEG_THRESHOLD_BASE = 1.5

# ==================== 止损参数 ====================

# ATR止损参数
ATR_PERIOD = 14              # ATR计算周期（天）
ATR_MULTIPLIER_BASE = 2.5    # ATR倍数（基础值）
ATR_MULTIPLIER_MIN = 1.5     # ATR倍数最小值
ATR_MULTIPLIER_MAX = 4.0     # ATR倍数最大值

# Beta调整系数
BETA_HIGH_THRESHOLD = 1.5    # 高Beta阈值
BETA_MID_HIGH_THRESHOLD = 1.2
BETA_LOW_THRESHOLD = 0.8
BETA_MID_LOW_THRESHOLD = 1.0

# Beta调整倍数
BETA_HIGH_MULTIPLIER = 1.2   # 高Beta股票的ATR倍数调整
BETA_MID_HIGH_MULTIPLIER = 1.1
BETA_LOW_MULTIPLIER = 0.8
BETA_MID_LOW_MULTIPLIER = 0.9

# 固定止损参数
FIXED_STOP_LOSS_PCT = 0.15   # 固定止损幅度（15%）

# ==================== 流动性参数 ====================

# 最小日均成交额（美元）
MIN_DAILY_VOLUME_USD = 5_000_000  # 500万美元

# 成交量异常阈值
VOLUME_ANOMALY_HIGH = 2.0    # 成交量超过历史平均2倍视为异常
VOLUME_ANOMALY_LOW = 0.3     # 成交量低于历史平均30%视为异常

# ==================== PE分位点参数 ====================

# PE分位点计算参数
PE_HISTORY_WINDOW_YEARS = 5  # 历史PE数据窗口（年）
PE_MIN_DATA_POINTS = 20      # 计算分位点所需的最少数据点

# PE分位点情绪评分映射
PE_PERCENTILE_SENTIMENT = {
    'very_low': (0, 20, 3.0),      # 0-20%: 3.0分
    'low': (20, 40, 4.5),          # 20-40%: 4.5分
    'neutral_low': (40, 60, 5.5),  # 40-60%: 5.5分
    'neutral_high': (60, 80, 6.5), # 60-80%: 6.5分
    'high': (80, 90, 8.0),         # 80-90%: 8.0分
    'very_high': (90, 100, 9.0),   # 90-100%: 9.0分
}

# Z分数调整阈值
PE_Z_SCORE_THRESHOLD = 2.0   # 超过2个标准差的调整阈值
PE_Z_SCORE_ADJUSTMENT = 0.5  # Z分数调整幅度

# ==================== 动态PEG参数 ====================

# 美债收益率阈值（%）
TREASURY_YIELD_HIGH_THRESHOLD = 4.0  # 高息环境阈值

# 高息环境下的PEG调整
HIGH_YIELD_PEG_ADJUSTMENT = 0.8  # 高息环境下降低20%（乘以0.8）

# ==================== 财报滞后性处理 ====================

# 财报发布后的数据滞后天数
EARNINGS_LAG_DAYS = 3  # 财报发布后3天内降低基本面权重

# 数据滞后时的权重调整
WEIGHT_BASELINE = {
    'fundamental': 0.40,  # 正常情况下的基本面权重
    'technical': 0.30,    # 正常情况下的技术面权重
    'sentiment': 0.30,    # 正常情况下的情绪权重
}

WEIGHT_EARNINGS_LAG = {
    'fundamental': 0.20,  # 财报滞后时的基本面权重（降低）
    'technical': 0.45,    # 财报滞后时的技术面权重（提高）
    'sentiment': 0.35,    # 财报滞后时的情绪权重（提高）
}

# ==================== 风险评分参数 ====================

# PE阈值
PE_HIGH_THRESHOLD = 40     # PE高于此值视为高风险
PE_VERY_HIGH_THRESHOLD = 60

# PEG阈值
PEG_HIGH_THRESHOLD = 2.0   # PEG高于此值视为高风险

# 增长率阈值
GROWTH_NEGATIVE_THRESHOLD = -0.10  # 增长率低于-10%视为高风险

# ==================== 市场情绪参数 ====================

# VIX阈值
VIX_HIGH = 30.0            # VIX高于30视为高风险
VIX_MEDIUM = 25.0          # VIX高于25视为中等风险
VIX_RISING = 20.0          # VIX高于20且快速上升

# Put/Call比率阈值
PUT_CALL_HIGH = 1.5        # Put/Call比率高于1.5视为高风险
PUT_CALL_MEDIUM = 1.2      # Put/Call比率高于1.2视为中等风险

# 美债收益率阈值
TREASURY_YIELD_VERY_HIGH = 5.0   # 美债收益率高于5.0%视为高风险
TREASURY_YIELD_HIGH = 4.5        # 美债收益率高于4.5%视为中等风险

# ==================== 市场差异化参数 ====================

# 市场配置 - 美股、港股、A股使用不同参数
MARKET_CONFIG = {
    'US': {  # 美股 - 基准参数
        'name': '美股',
        'name_en': 'US Market',
        'min_daily_volume_usd': 5_000_000,    # 最小日成交额（美元）
        'risk_premium': 1.0,                   # 风险溢价系数（基准）
        'growth_discount': 0.6,                # 增长率折现系数
        'pe_high_threshold': 40,               # PE高风险阈值
        'pe_very_high_threshold': 60,          # PE极高风险阈值
        'liquidity_coefficient': 1.0,          # 流动性系数
        'volatility_adjustment': 1.0,          # 波动率调整
        'currency': 'USD',
        'trading_hours': 'US_MARKET',
    },
    'CN': {  # A股 - 中国大陆市场
        'name': 'A股',
        'name_en': 'China A-Share',
        'min_daily_volume_usd': 1_000_000,    # 放宽流动性要求（A股单位换算）
        'risk_premium': 1.3,                   # 政策风险加成
        'growth_discount': 0.7,                # 更激进的增长折现（A股偏好成长）
        'pe_high_threshold': 50,               # A股PE普遍更高
        'pe_very_high_threshold': 80,
        'liquidity_coefficient': 0.5,          # 流动性要求降低
        'volatility_adjustment': 1.2,          # 波动率更高
        'policy_risk_factor': 1.2,             # 政策敏感度
        'currency': 'CNY',
        'trading_hours': 'CN_MARKET',
    },
    'HK': {  # 港股 - 香港市场
        'name': '港股',
        'name_en': 'Hong Kong',
        'min_daily_volume_usd': 2_000_000,    # 港股流动性中等
        'risk_premium': 1.15,                  # 风险溢价略高
        'growth_discount': 0.65,               # 增长折现中等
        'pe_high_threshold': 35,               # 港股PE相对较低
        'pe_very_high_threshold': 50,
        'liquidity_coefficient': 0.6,          # 流动性要求中等
        'volatility_adjustment': 1.1,          # 波动率略高
        'discount_factor': 0.95,               # 港股折让（H股 vs A股）
        'fx_risk_coefficient': 0.1,            # 汇率风险（港币挂钩美元）
        'currency': 'HKD',
        'trading_hours': 'HK_MARKET',
    }
}

# 市场风格偏好权重
MARKET_STYLE_WEIGHTS = {
    'US': {  # 美股 - 均衡
        'quality': 1.0,
        'value': 1.0,
        'growth': 1.0,
        'momentum': 1.0,
        'balanced': 1.0
    },
    'CN': {  # A股 - 偏好成长和动量
        'quality': 0.8,
        'value': 0.7,
        'growth': 1.3,
        'momentum': 1.2,
        'balanced': 1.0
    },
    'HK': {  # 港股 - 偏好价值和质量
        'quality': 1.2,
        'value': 1.3,
        'growth': 0.9,
        'momentum': 0.8,
        'balanced': 1.0
    }
}

# ==================== 市场识别规则 ====================

# 股票代码后缀到市场的映射
TICKER_SUFFIX_TO_MARKET = {
    '.SS': 'CN',   # 上海证券交易所
    '.SZ': 'CN',   # 深圳证券交易所
    '.HK': 'HK',   # 香港交易所
    '.T': 'JP',    # 东京证券交易所（暂不支持）
    '.L': 'UK',    # 伦敦证券交易所（暂不支持）
}

# A股代码前缀规则
CN_STOCK_PREFIX_RULES = {
    '60': 'SS',    # 上海主板
    '68': 'SS',    # 上海科创板
    '00': 'SZ',    # 深圳主板
    '30': 'SZ',    # 深圳创业板
}

# ==================== 辅助函数 ====================

def detect_market_from_ticker(ticker: str) -> str:
    """
    根据股票代码识别市场

    Args:
        ticker: 股票代码

    Returns:
        市场代码 ('US', 'CN', 'HK')
    """
    ticker = ticker.upper().strip()

    # 检查后缀
    for suffix, market in TICKER_SUFFIX_TO_MARKET.items():
        if ticker.endswith(suffix.upper()):
            return market

    # 检查是否是纯数字（可能是A股）
    base_ticker = ticker.split('.')[0]
    if base_ticker.isdigit() and len(base_ticker) == 6:
        prefix = base_ticker[:2]
        if prefix in CN_STOCK_PREFIX_RULES:
            return 'CN'

    # 默认为美股
    return 'US'


def get_market_config(market: str) -> dict:
    """
    获取市场配置

    Args:
        market: 市场代码

    Returns:
        市场配置字典
    """
    return MARKET_CONFIG.get(market, MARKET_CONFIG['US'])


def get_market_style_weights(market: str) -> dict:
    """
    获取市场风格权重

    Args:
        market: 市场代码

    Returns:
        风格权重字典
    """
    return MARKET_STYLE_WEIGHTS.get(market, MARKET_STYLE_WEIGHTS['US'])


def adjust_parameter_for_market(base_value: float, market: str, param_type: str) -> float:
    """
    根据市场调整参数

    Args:
        base_value: 基础参数值
        market: 市场代码
        param_type: 参数类型 ('risk', 'growth', 'pe', 'liquidity')

    Returns:
        调整后的参数值
    """
    config = get_market_config(market)

    if param_type == 'risk':
        return base_value * config.get('risk_premium', 1.0)
    elif param_type == 'growth':
        return base_value * config.get('growth_discount', 0.6) / 0.6  # 相对于基准调整
    elif param_type == 'pe':
        # PE阈值直接使用市场配置
        return config.get('pe_high_threshold', base_value)
    elif param_type == 'liquidity':
        return base_value * config.get('liquidity_coefficient', 1.0)
    else:
        return base_value
