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


