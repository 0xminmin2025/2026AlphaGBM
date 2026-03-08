"""
板块ETF映射配置

将各市场的板块与对应的ETF代码关联，用于板块轮动分析。
使用ETF作为板块代理，获取板块级别的行情数据。
"""

from typing import Dict, Optional

# ==================== 美股板块ETF映射 ====================

US_SECTOR_ETFS: Dict[str, str] = {
    # SPDR Select Sector ETFs (11 GICS Sectors)
    'Technology': 'XLK',              # Technology Select Sector SPDR Fund
    'Healthcare': 'XLV',              # Health Care Select Sector SPDR Fund
    'Financials': 'XLF',              # Financial Select Sector SPDR Fund
    'Consumer_Discretionary': 'XLY',  # Consumer Discretionary Select Sector SPDR Fund
    'Consumer_Staples': 'XLP',        # Consumer Staples Select Sector SPDR Fund
    'Energy': 'XLE',                  # Energy Select Sector SPDR Fund
    'Industrials': 'XLI',             # Industrial Select Sector SPDR Fund
    'Materials': 'XLB',               # Materials Select Sector SPDR Fund
    'Utilities': 'XLU',               # Utilities Select Sector SPDR Fund
    'Real_Estate': 'XLRE',            # Real Estate Select Sector SPDR Fund
    'Communication_Services': 'XLC',  # Communication Services Select Sector SPDR Fund

    # Specialized/Thematic ETFs
    'Semiconductors': 'SMH',          # VanEck Semiconductor ETF
    'Software': 'IGV',                # iShares Expanded Tech-Software Sector ETF
    'Biotech': 'XBI',                 # SPDR S&P Biotech ETF
    'Clean_Energy': 'ICLN',           # iShares Global Clean Energy ETF
    'Cybersecurity': 'HACK',          # ETFMG Prime Cyber Security ETF
    'AI_Robotics': 'BOTZ',            # Global X Robotics & AI ETF
    'Cloud_Computing': 'SKYY',        # First Trust Cloud Computing ETF
    'Gold_Miners': 'GDX',             # VanEck Gold Miners ETF
    'Regional_Banks': 'KRE',          # SPDR S&P Regional Banking ETF
    'Homebuilders': 'XHB',            # SPDR S&P Homebuilders ETF
    'Retail': 'XRT',                  # SPDR S&P Retail ETF
    'Transportation': 'IYT',          # iShares Transportation Average ETF
    'Defense_Aerospace': 'ITA',       # iShares U.S. Aerospace & Defense ETF
    'Internet': 'FDN',                # First Trust Dow Jones Internet Index Fund
}

# ==================== 港股板块ETF映射 ====================

HK_SECTOR_ETFS: Dict[str, str] = {
    # 恒生指数系列ETF
    'Technology': '3067.HK',          # 安硕恒生科技指数ETF
    'Healthcare': '3174.HK',          # 华夏恒生生物科技指数ETF
    'Financials': '2830.HK',          # 安硕金融ETF
    'Consumer': '2812.HK',            # 南方中国消费指数ETF
    'Energy': '3053.HK',              # 南方能源ETF (如存在)
    'Real_Estate': '2836.HK',         # 安硕恒生房地产指数ETF
    'Infrastructure': '2820.HK',      # 安硕中国基建ETF

    # 主题ETF
    'New_Economy': '3069.HK',         # 安硕中国新经济ETF
    'Internet': '3086.HK',            # 华夏恒生互联网ETF
    'EV_Auto': '3173.HK',             # 易方达中国新能源汽车ETF
    'Semiconductors': '3191.HK',      # 安硕恒生半导体ETF (如存在)
}

# ==================== A股板块ETF映射 ====================

CN_SECTOR_ETFS: Dict[str, str] = {
    # 行业ETF（沪深交易所）
    'Technology': '512760.SS',        # 科技ETF
    'Healthcare': '512010.SS',        # 医药ETF
    'Financials': '512640.SS',        # 金融ETF
    'Consumer': '510630.SS',          # 消费ETF
    'Energy': '512580.SS',            # 能源ETF
    'Materials': '510630.SS',         # 材料ETF
    'Industrials': '512660.SS',       # 军工ETF
    'Real_Estate': '512200.SS',       # 房地产ETF
    'Utilities': '512580.SS',         # 公用事业ETF (与能源共用)

    # 主题/热门赛道ETF
    'Semiconductors': '512480.SS',    # 半导体ETF
    'New_Energy': '516160.SS',        # 新能源ETF
    'EV_Battery': '159755.SZ',        # 新能源车ETF
    'Biotech': '512290.SS',           # 生物医药ETF
    'AI_Computing': '562190.SS',      # 人工智能ETF (如存在)
    'Software': '515230.SS',          # 软件ETF
    'Internet': '513050.SS',          # 中概互联ETF
    'Bank': '512800.SS',              # 银行ETF
    'Securities': '512880.SS',        # 券商ETF
    'Insurance': '512070.SS',         # 保险ETF
    'Liquor': '512690.SS',            # 白酒ETF
    'Photovoltaic': '515790.SS',      # 光伏ETF
    'Military': '512660.SS',          # 军工ETF
}

# ==================== 完整板块ETF映射表 ====================

SECTOR_ETF_MAPPING: Dict[str, Dict[str, str]] = {
    'US': US_SECTOR_ETFS,
    'HK': HK_SECTOR_ETFS,
    'CN': CN_SECTOR_ETFS,
}

# ==================== 市场基准指数 ====================

SECTOR_BENCHMARKS: Dict[str, str] = {
    'US': 'SPY',       # S&P 500 ETF
    'HK': '2800.HK',   # 盈富基金（追踪恒生指数）
    'CN': '510300.SS', # 沪深300ETF
}

# ==================== 板块中文名称映射 ====================

SECTOR_NAMES_ZH: Dict[str, str] = {
    # 美股11大板块
    'Technology': '科技',
    'Healthcare': '医疗保健',
    'Financials': '金融',
    'Consumer_Discretionary': '可选消费',
    'Consumer_Staples': '必需消费',
    'Energy': '能源',
    'Industrials': '工业',
    'Materials': '基础材料',
    'Utilities': '公用事业',
    'Real_Estate': '房地产',
    'Communication_Services': '通信服务',

    # 细分板块
    'Semiconductors': '半导体',
    'Software': '软件',
    'Biotech': '生物科技',
    'Clean_Energy': '清洁能源',
    'Cybersecurity': '网络安全',
    'AI_Robotics': 'AI与机器人',
    'Cloud_Computing': '云计算',
    'Gold_Miners': '黄金矿业',
    'Regional_Banks': '区域银行',
    'Homebuilders': '房屋建筑',
    'Retail': '零售',
    'Transportation': '交通运输',
    'Defense_Aerospace': '国防航空',
    'Internet': '互联网',

    # 港股特有
    'New_Economy': '新经济',
    'Infrastructure': '基建',
    'EV_Auto': '新能源汽车',

    # A股特有
    'Consumer': '消费',
    'New_Energy': '新能源',
    'EV_Battery': '新能源车电池',
    'AI_Computing': '人工智能',
    'Bank': '银行',
    'Securities': '券商',
    'Insurance': '保险',
    'Liquor': '白酒',
    'Photovoltaic': '光伏',
    'Military': '军工',
}

# ==================== 板块分类映射（股票板块 -> ETF板块） ====================

# yfinance返回的sector字段到我们ETF映射的转换
YFINANCE_SECTOR_TO_ETF_SECTOR: Dict[str, str] = {
    'Technology': 'Technology',
    'Healthcare': 'Healthcare',
    'Financial Services': 'Financials',
    'Financials': 'Financials',
    'Consumer Cyclical': 'Consumer_Discretionary',
    'Consumer Discretionary': 'Consumer_Discretionary',
    'Consumer Defensive': 'Consumer_Staples',
    'Consumer Staples': 'Consumer_Staples',
    'Energy': 'Energy',
    'Industrials': 'Industrials',
    'Basic Materials': 'Materials',
    'Materials': 'Materials',
    'Utilities': 'Utilities',
    'Real Estate': 'Real_Estate',
    'Communication Services': 'Communication_Services',
}

# 行业到细分板块的映射（用于更精准的板块定位）
INDUSTRY_TO_SUBSECTOR: Dict[str, str] = {
    'Semiconductors': 'Semiconductors',
    'Semiconductor Equipment & Materials': 'Semiconductors',
    'Software—Application': 'Software',
    'Software—Infrastructure': 'Software',
    'Biotechnology': 'Biotech',
    'Drug Manufacturers—General': 'Healthcare',
    'Banks—Regional': 'Regional_Banks',
    'Banks—Diversified': 'Financials',
    'Internet Content & Information': 'Internet',
    'Internet Retail': 'Internet',
    'Aerospace & Defense': 'Defense_Aerospace',
    'Solar': 'Clean_Energy',
    'Auto Manufacturers': 'Consumer_Discretionary',
    'Residential Construction': 'Homebuilders',
    'Specialty Retail': 'Retail',
}


# ==================== 辅助函数 ====================

def get_sector_etfs(market: str = 'US') -> Dict[str, str]:
    """
    获取指定市场的板块ETF映射

    Args:
        market: 市场代码 ('US', 'HK', 'CN')

    Returns:
        板块到ETF代码的映射字典
    """
    return SECTOR_ETF_MAPPING.get(market, US_SECTOR_ETFS)


def get_benchmark_ticker(market: str = 'US') -> str:
    """
    获取指定市场的基准指数ETF代码

    Args:
        market: 市场代码 ('US', 'HK', 'CN')

    Returns:
        基准指数ETF代码
    """
    return SECTOR_BENCHMARKS.get(market, 'SPY')


def get_sector_name_zh(sector: str) -> str:
    """
    获取板块的中文名称

    Args:
        sector: 英文板块名称

    Returns:
        中文板块名称
    """
    return SECTOR_NAMES_ZH.get(sector, sector)


def map_yfinance_sector(yf_sector: str) -> str:
    """
    将yfinance返回的板块名称映射到我们的ETF板块

    Args:
        yf_sector: yfinance返回的sector字段

    Returns:
        映射后的板块名称
    """
    return YFINANCE_SECTOR_TO_ETF_SECTOR.get(yf_sector, 'Technology')


def get_subsector_from_industry(industry: str) -> Optional[str]:
    """
    根据行业获取细分板块

    Args:
        industry: yfinance返回的industry字段

    Returns:
        细分板块名称，如无匹配则返回None
    """
    return INDUSTRY_TO_SUBSECTOR.get(industry)


def get_etf_for_stock(sector: str, industry: Optional[str] = None, market: str = 'US') -> str:
    """
    根据股票的板块和行业获取对应的ETF代码

    优先使用行业对应的细分板块ETF，如无则使用大板块ETF

    Args:
        sector: 股票所属板块
        industry: 股票所属行业（可选）
        market: 市场代码

    Returns:
        ETF代码
    """
    etfs = get_sector_etfs(market)

    # 优先检查行业对应的细分板块
    if industry:
        subsector = get_subsector_from_industry(industry)
        if subsector and subsector in etfs:
            return etfs[subsector]

    # 映射板块名称
    mapped_sector = map_yfinance_sector(sector)

    # 返回对应ETF
    return etfs.get(mapped_sector, etfs.get('Technology', 'SPY'))
