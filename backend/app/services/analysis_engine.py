import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import logging

# 导入yfinance的异常类
try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:
    # 如果导入失败，定义一个占位符
    YFRateLimitError = type('YFRateLimitError', (Exception,), {})

# 导入配置参数
# 导入配置参数
try:
    from ..constants import *
except ImportError:
    # 尝试从同级导入（用于单独测试）
    try:
        from constants import *
    except ImportError:
    # 如果config.py不存在，使用默认值（向后兼容）
        GROWTH_DISCOUNT_FACTOR = 0.6
        ATR_MULTIPLIER_BASE = 2.5
        MIN_DAILY_VOLUME_USD = 5_000_000
        FIXED_STOP_LOSS_PCT = 0.15
        PEG_THRESHOLD_BASE = 1.5


def check_liquidity(data, currency_symbol='$', ticker=None):
    """
    检查股票流动性，判断是否满足交易要求
    根据不同市场（美股、港股、A股）使用差异化的流动性门槛

    参数:
        data: 包含市场数据的字典
        currency_symbol: 货币符号，用于计算成交额
        ticker: 股票代码（用于识别市场）

    返回:
        (is_liquid, liquidity_info)
        is_liquid: 是否满足流动性要求
        liquidity_info: 流动性信息字典
    """
    try:
        # 识别市场类型并获取对应的流动性门槛
        symbol = ticker or data.get('symbol', '') or data.get('original_symbol', '')
        market = detect_market_from_ticker(symbol)
        market_config = get_market_config(market)

        # 获取市场对应的流动性门槛
        min_daily_volume = market_config.get('min_daily_volume_usd', MIN_DAILY_VOLUME_USD)
        liquidity_coefficient = market_config.get('liquidity_coefficient', 1.0)
        market_name = market_config.get('name', market)
        currency = market_config.get('currency', 'USD')

        # 调整后的门槛（考虑流动性系数）
        adjusted_threshold = min_daily_volume * liquidity_coefficient

        print(f"[流动性检查] {symbol}: 市场={market_name}, 门槛=${adjusted_threshold:,.0f}, 系数={liquidity_coefficient}")

        # 获取历史数据中的成交量
        if 'history_prices' in data and len(data.get('history_prices', [])) > 0:
            # 从历史数据计算平均成交量
            # 注意：这里需要实际的历史成交量数据
            # 如果数据中没有，尝试从其他来源获取
            pass

        # 尝试从volume_anomaly获取
        volume_anomaly = data.get('volume_anomaly')
        if volume_anomaly and volume_anomaly.get('historical_avg'):
            # 估算日均成交额（成交量 * 当前价格）
            avg_volume = volume_anomaly['historical_avg']
            current_price = data.get('price', 0)

            if current_price > 0:
                # 估算日均成交额
                estimated_daily_volume = avg_volume * current_price

                # 对于非美元市场，需要换算（假设价格已经是本币）
                # 这里简化处理：假设数据源已经是统一的美元或本币
                if currency == 'CNY':
                    # A股：假设价格是人民币，门槛也是人民币
                    # 但 min_daily_volume_usd 是美元，需要换算
                    # 简化：直接使用人民币门槛（约为美元门槛的7倍）
                    # 实际应该从配置读取或动态汇率
                    estimated_daily_volume_usd = estimated_daily_volume / 7.0  # 粗略汇率换算
                elif currency == 'HKD':
                    # 港股：港币换算
                    estimated_daily_volume_usd = estimated_daily_volume / 7.8  # 粗略汇率
                else:
                    estimated_daily_volume_usd = estimated_daily_volume

                # 检查是否满足最低流动性要求
                is_liquid = estimated_daily_volume_usd >= adjusted_threshold

                print(f"[流动性检查] {symbol}: 日均成交额=${estimated_daily_volume_usd:,.0f}, 满足要求={is_liquid}")

                return is_liquid, {
                    'estimated_daily_volume_usd': estimated_daily_volume_usd,
                    'estimated_daily_volume_local': estimated_daily_volume,
                    'min_required_usd': adjusted_threshold,
                    'base_threshold': min_daily_volume,
                    'liquidity_coefficient': liquidity_coefficient,
                    'market': market,
                    'market_name': market_name,
                    'currency': currency,
                    'meets_requirement': is_liquid
                }

        # 如果无法获取成交量数据，返回默认值（允许交易，但标记为未知）
        return True, {
            'estimated_daily_volume_usd': None,
            'min_required_usd': adjusted_threshold,
            'market': market,
            'market_name': market_name,
            'meets_requirement': True,
            'warning': '无法获取成交量数据，流动性检查已跳过'
        }
    except Exception as e:
        print(f"流动性检查出错: {e}")
        # 出错时默认允许交易
        return True, {'error': str(e)}


def calculate_pe_percentile(current_pe, hist_data=None, ticker=None):
    """
    计算PE分位点（历史PE百分位）

    参数:
        current_pe: 当前PE值
        hist_data: 历史数据DataFrame（可选，如果有的话可以计算历史PE）
        ticker: 股票代码（可选，用于获取历史数据）

    返回:
        (pe_percentile, pe_z_score, historical_pe_list)
        pe_percentile: PE百分位（0-100）
        pe_z_score: Z分数
        historical_pe_list: 历史PE列表（如果可用）
    """
    import numpy as np

    historical_pe_list = []

    # 方法1: 尝试使用ticker获取历史盈利数据计算PE序列
    if ticker is not None:
        try:
            stock = yf.Ticker(ticker)

            # 获取5年历史价格
            hist_prices = stock.history(period="5y")
            if hist_prices.empty:
                print(f"[PE分位点] {ticker}: 无法获取历史价格数据")
            else:
                # 获取季度盈利数据
                earnings = None
                try:
                    earnings = stock.quarterly_earnings
                except Exception as e:
                    print(f"[PE分位点] {ticker}: 获取季度盈利失败 - {e}")

                if earnings is not None and not earnings.empty:
                    # 遍历每个盈利报告期，计算历史PE
                    for date, row in earnings.iterrows():
                        eps = row.get('Earnings', 0)
                        if eps is not None and eps > 0:
                            try:
                                # 找到该日期附近的收盘价
                                # 转换日期格式以匹配
                                report_date = pd.Timestamp(date)

                                # 找最近的交易日价格
                                price_mask = hist_prices.index <= report_date
                                if price_mask.any():
                                    price_at_date = hist_prices.loc[price_mask, 'Close'].iloc[-1]
                                    # 年化EPS计算PE (季度EPS * 4)
                                    annual_eps = eps * 4
                                    pe = price_at_date / annual_eps

                                    # 过滤异常值 (PE在0-200之间)
                                    if 0 < pe < 200:
                                        historical_pe_list.append(pe)
                            except Exception as e:
                                continue

                    if len(historical_pe_list) >= 4:
                        print(f"[PE分位点] {ticker}: 从盈利数据计算得到 {len(historical_pe_list)} 个历史PE点")

                # 方法2: 如果盈利数据不足，尝试使用info中的trailingPE历史
                if len(historical_pe_list) < PE_MIN_DATA_POINTS:
                    try:
                        info = stock.info
                        trailing_pe = info.get('trailingPE')
                        forward_pe = info.get('forwardPE')

                        # 使用当前PE和远期PE构建简单的历史参考
                        if trailing_pe and trailing_pe > 0 and trailing_pe < 200:
                            # 基于行业中位数PE和当前PE构建历史分布估计
                            # 假设PE在历史中的波动范围约为±30%
                            pe_estimates = []
                            base_pe = trailing_pe

                            # 生成模拟历史PE分布（基于合理假设）
                            # 这是一个fallback方案，当真实历史数据不可用时
                            for factor in [0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3]:
                                simulated_pe = base_pe * factor
                                if 0 < simulated_pe < 200:
                                    pe_estimates.append(simulated_pe)

                            if forward_pe and forward_pe > 0 and forward_pe < 200:
                                pe_estimates.append(forward_pe)

                            if len(pe_estimates) >= 5:
                                historical_pe_list = pe_estimates
                                print(f"[PE分位点] {ticker}: 使用估算方法生成 {len(pe_estimates)} 个PE参考点")
                    except Exception as e:
                        print(f"[PE分位点] {ticker}: 估算方法失败 - {e}")

        except Exception as e:
            print(f"[PE分位点] {ticker}: 获取数据失败 - {e}")

    # 数据不足，返回中性值
    if len(historical_pe_list) < 5:
        print(f"[PE分位点] {ticker if ticker else 'unknown'}: 历史PE数据不足({len(historical_pe_list)}个)，返回默认50%")
        return 50.0, 0.0, []

    # 计算百分位
    # 使用 scipy.stats.percentileofscore 更精确
    try:
        from scipy import stats
        pe_percentile = stats.percentileofscore(historical_pe_list, current_pe, kind='rank')
    except ImportError:
        # fallback: 手动计算
        pe_percentile = (sum(1 for pe in historical_pe_list if pe < current_pe) / len(historical_pe_list)) * 100

    # 计算Z分数
    mean_pe = np.mean(historical_pe_list)
    std_pe = np.std(historical_pe_list)
    if std_pe > 0:
        pe_z_score = (current_pe - mean_pe) / std_pe
    else:
        pe_z_score = 0.0

    print(f"[PE分位点] {ticker if ticker else 'unknown'}: 当前PE={current_pe:.2f}, 分位点={pe_percentile:.1f}%, Z分数={pe_z_score:.2f}")

    return pe_percentile, pe_z_score, historical_pe_list


def get_pe_sentiment_from_percentile(pe_percentile, pe_z_score):
    """
    基于PE分位点计算市场情绪分数
    
    参数:
        pe_percentile: PE百分位（0-100）
        pe_z_score: Z分数
    
    返回:
        市场情绪分数（0-10）
    """
    # 根据PE分位点确定基础情绪分数
    if pe_percentile < 20:
        base_sentiment = PE_PERCENTILE_SENTIMENT['very_low'][2]
    elif pe_percentile < 40:
        base_sentiment = PE_PERCENTILE_SENTIMENT['low'][2]
    elif pe_percentile < 60:
        base_sentiment = PE_PERCENTILE_SENTIMENT['neutral_low'][2]
    elif pe_percentile < 80:
        base_sentiment = PE_PERCENTILE_SENTIMENT['neutral_high'][2]
    elif pe_percentile < 90:
        base_sentiment = PE_PERCENTILE_SENTIMENT['high'][2]
    else:
        base_sentiment = PE_PERCENTILE_SENTIMENT['very_high'][2]
    
    # Z分数调整（极端偏离时进一步调整）
    if abs(pe_z_score) > PE_Z_SCORE_THRESHOLD:
        if pe_z_score > 0:
            base_sentiment = min(10.0, base_sentiment + PE_Z_SCORE_ADJUSTMENT)
        else:
            base_sentiment = max(0.0, base_sentiment - PE_Z_SCORE_ADJUSTMENT)
    
    return base_sentiment


def get_dynamic_peg_threshold(macro_data=None):
    """
    根据美债收益率动态调整PEG阈值
    
    参数:
        macro_data: 宏观经济数据（包含treasury_10y）
    
    返回:
        动态PEG阈值
    """
    base_threshold = PEG_THRESHOLD_BASE  # 默认1.5
    
    if macro_data and macro_data.get('treasury_10y'):
        treasury_yield = macro_data['treasury_10y']
        
        # 简化版：高息环境模式
        # 如果美债收益率>4%，降低PEG阈值20%
        if treasury_yield >= TREASURY_YIELD_HIGH_THRESHOLD:
            return base_threshold * HIGH_YIELD_PEG_ADJUSTMENT
        else:
            return base_threshold
    else:
        return base_threshold


def get_ipo_lockup_data(info, ticker):
    """
    获取IPO与解禁监控数据
    
    参数:
        info: yfinance获取的股票信息
        ticker: 标准化后的股票代码
    
    返回:
        lockup_data字典，包含：
        - ipo_date: IPO日期
        - lockup_expiry_date: 解禁日期
        - days_until_lockup: 距离解禁期的天数
        - is_lockup_risk: 是否处于解禁风险期（< 14天）
        - lockup_shares_ratio: 解禁股数占总股本比例（A股）
    """
    lockup_data = {
        'ipo_date': None,
        'lockup_expiry_date': None,
        'days_until_lockup': None,
        'is_lockup_risk': False,
        'lockup_shares_ratio': None,
        'lockup_events': []  # A股解禁事件列表
    }
    
    from datetime import datetime, timedelta
    
    # 判断市场类型
    is_us_market = '.' not in ticker or ticker.endswith(('.US'))
    is_hk_market = ticker.endswith('.HK')
    is_cn_market = ticker.endswith('.SS') or ticker.endswith('.SZ')
    
    # 美股/港股逻辑：IPO日期 + 180天
    if is_us_market or is_hk_market:
        try:
            # 从info获取IPO日期
            ipo_date_str = info.get('ipoDate')
            if ipo_date_str:
                # 处理不同的日期格式
                if isinstance(ipo_date_str, (int, float)):
                    # 可能是时间戳
                    ipo_date = datetime.fromtimestamp(ipo_date_str).date()
                elif isinstance(ipo_date_str, str):
                    # 尝试解析日期字符串
                    try:
                        ipo_date = datetime.strptime(ipo_date_str, '%Y-%m-%d').date()
                    except:
                        try:
                            ipo_date = datetime.strptime(ipo_date_str, '%Y-%m-%d %H:%M:%S').date()
                        except:
                            ipo_date = None
                else:
                    ipo_date = None
                
                if ipo_date:
                    # 计算解禁日期（IPO日期 + 180天）
                    lockup_expiry_date = ipo_date + timedelta(days=180)
                    today = datetime.now().date()
                    days_until_lockup = (lockup_expiry_date - today).days
                    
                    lockup_data['ipo_date'] = ipo_date.strftime('%Y-%m-%d')
                    lockup_data['lockup_expiry_date'] = lockup_expiry_date.strftime('%Y-%m-%d')
                    lockup_data['days_until_lockup'] = days_until_lockup
                    lockup_data['is_lockup_risk'] = 0 <= days_until_lockup < 14
        except Exception as e:
            print(f"获取IPO/解禁数据失败（美股/港股）: {e}")
    
    # A股逻辑：使用AkShare数据抓取
    elif is_cn_market:
        try:
            import akshare as ak
            # 提取A股代码（去掉.SS或.SZ后缀）
            cn_code = ticker.replace('.SS', '').replace('.SZ', '')
            
            # 尝试获取限售股解禁数据
            try:
                # 注意：这个接口可能需要特定的参数格式
                # 如果接口不可用，可以尝试其他方法
                lockup_summary = ak.stock_restricted_shares_summary_em(symbol=cn_code)
                
                if lockup_summary is not None and len(lockup_summary) > 0:
                    today = datetime.now().date()
                    lockup_events = []
                    
                    for _, row in lockup_summary.iterrows():
                        try:
                            expiry_date_str = str(row.get('解禁日期', ''))
                            if expiry_date_str and expiry_date_str != 'nan':
                                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                                days_until = (expiry_date - today).days
                                
                                # 只保留未来的解禁日期
                                if days_until >= 0:
                                    lockup_shares = row.get('解禁股数', 0)
                                    lockup_ratio = row.get('解禁股数占总股本比例', 0)
                                    
                                    lockup_events.append({
                                        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                                        'days_until': days_until,
                                        'lockup_shares': lockup_shares,
                                        'lockup_ratio': lockup_ratio,
                                        'lockup_type': row.get('解禁类型', '未知')
                                    })
                        except:
                            continue
                    
                    # 按日期排序，获取最近的解禁日期
                    if lockup_events:
                        lockup_events.sort(key=lambda x: x['days_until'])
                        next_lockup = lockup_events[0]
                        
                        lockup_data['lockup_expiry_date'] = next_lockup['expiry_date']
                        lockup_data['days_until_lockup'] = next_lockup['days_until']
                        lockup_data['is_lockup_risk'] = 0 <= next_lockup['days_until'] < 14
                        lockup_data['lockup_shares_ratio'] = next_lockup.get('lockup_ratio', 0)
                        lockup_data['lockup_events'] = lockup_events
            except Exception as e:
                print(f"获取A股解禁数据失败（AkShare）: {e}")
                # 如果AkShare接口不可用，尝试从其他数据源获取
                # 或者使用默认值
        except ImportError:
            print("警告: AkShare未安装，无法获取A股解禁数据")
        except Exception as e:
            print(f"获取A股解禁数据失败: {e}")
    
    return lockup_data


def infer_industry_from_name(name, symbol):
    """
    根据公司名称和股票代码推断行业信息
    用于新上市公司或数据源缺失的情况
    
    返回: (sector, industry) 元组
    """
    if not name:
        return None, None
    
    name_lower = name.lower()
    symbol_lower = symbol.lower() if symbol else ''
    
    # 科技/半导体相关关键词
    tech_keywords = {
        'semiconductor': ['芯片', '半导体', 'ic', '集成电路', 'chip', 'semiconductor', 'gpu', 'cpu', 'ai芯片', '图形处理器', 'thread', '线程', '图形', 'graphics', '处理器', 'processor', '算力', '计算'],
        'software': ['软件', 'software', 'saas', '云计算', 'cloud', '平台', 'platform'],
        'internet': ['互联网', 'internet', '电商', 'e-commerce', '社交', 'social', '媒体', 'media'],
        'hardware': ['硬件', 'hardware', '设备', 'equipment', '终端', '终端设备'],
        'ai_ml': ['人工智能', 'artificial intelligence', 'ai', '机器学习', 'machine learning', 'deep learning', '深度学习'],
        'gaming': ['游戏', 'game', 'gaming', '娱乐', 'entertainment']
    }
    
    # 医疗相关
    healthcare_keywords = {
        'pharmaceutical': ['制药', 'pharmaceutical', '药', 'medicine', '药品'],
        'biotech': ['生物', 'biotech', 'biotechnology', '生物技术', '生物医药'],
        'medical_device': ['医疗设备', 'medical device', '医疗器械', '医疗仪器']
    }
    
    # 金融相关
    finance_keywords = {
        'bank': ['银行', 'bank', 'banking'],
        'insurance': ['保险', 'insurance', 'insurer'],
        'securities': ['证券', 'securities', '券商', 'brokerage']
    }
    
    # 能源相关
    energy_keywords = {
        'oil_gas': ['石油', 'oil', '天然气', 'gas', '石化', 'petrochemical'],
        'new_energy': ['新能源', 'new energy', '光伏', 'solar', '风电', 'wind', '电池', 'battery', '锂电池']
    }
    
    # 消费相关
    consumer_keywords = {
        'retail': ['零售', 'retail', '消费', 'consumer'],
        'food_beverage': ['食品', 'food', '饮料', 'beverage', '餐饮', 'restaurant']
    }
    
    # 检查科技类
    for sub_ind, keywords in tech_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            if sub_ind == 'semiconductor':
                return 'Technology', 'Semiconductors'
            elif sub_ind == 'software':
                return 'Technology', 'Software'
            elif sub_ind == 'internet':
                return 'Technology', 'Internet'
            elif sub_ind == 'ai_ml':
                return 'Technology', 'Artificial Intelligence'
            elif sub_ind == 'gaming':
                return 'Technology', 'Interactive Media & Services'
            else:
                return 'Technology', 'Technology Hardware'
    
    # 检查医疗类
    for sub_ind, keywords in healthcare_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            if sub_ind == 'biotech':
                return 'Healthcare', 'Biotechnology'
            elif sub_ind == 'medical_device':
                return 'Healthcare', 'Medical Devices'
            else:
                return 'Healthcare', 'Pharmaceuticals'
    
    # 检查金融类
    for sub_ind, keywords in finance_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            if sub_ind == 'bank':
                return 'Financial Services', 'Banks'
            elif sub_ind == 'insurance':
                return 'Financial Services', 'Insurance'
            else:
                return 'Financial Services', 'Capital Markets'
    
    # 检查能源类
    for sub_ind, keywords in energy_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            if sub_ind == 'new_energy':
                return 'Energy', 'Renewable Energy'
            else:
                return 'Energy', 'Oil & Gas'
    
    # 检查消费类
    for sub_ind, keywords in consumer_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            if sub_ind == 'food_beverage':
                return 'Consumer Defensive', 'Food & Beverages'
            else:
                return 'Consumer Cyclical', 'Retail'
    
    # A股代码规则推断
    if symbol_lower.endswith('.ss') or symbol_lower.endswith('.sz'):
        code = symbol_lower.replace('.ss', '').replace('.sz', '')
        if code.startswith('688'):
            # 科创板，通常是科技类，根据名称进一步细分
            if any(kw in name_lower for kw in ['芯片', '半导体', 'chip', 'gpu', 'cpu', '集成电路', 'ic', 'thread', '线程']):
                return 'Technology', 'Semiconductors'
            elif any(kw in name_lower for kw in ['软件', 'software', '云计算', 'cloud', 'saas']):
                return 'Technology', 'Software'
            elif any(kw in name_lower for kw in ['人工智能', 'ai', 'machine learning', '机器学习']):
                return 'Technology', 'Artificial Intelligence'
            else:
                return 'Technology', 'Technology'
        elif code.startswith('300'):
            # 创业板，可能是科技或医疗
            if any(kw in name_lower for kw in ['医疗', '生物', 'medical', 'biotech']):
                return 'Healthcare', 'Healthcare'
            return 'Technology', 'Technology'
        elif code.startswith(('600', '601', '603')):
            # 上交所主板，可能多种行业
            pass
        elif code.startswith(('000', '001', '002')):
            # 深交所主板/中小板
            pass
    
    # 无法推断
    return None, None


def normalize_ticker(ticker):
    """
    标准化股票代码格式
    自动识别市场并添加后缀
    支持模糊搜索，包括港股前面补0的情况（如02525 -> 2525.HK）
    """
    ticker = ticker.strip().upper()
    
    # 如果已经包含市场后缀，直接返回
    if '.' in ticker:
        return ticker
    
    # 判断市场类型
    # 港股：支持4-5位数字，包括前面有0的情况（如09988 -> 9988.HK，02525 -> 2525.HK）
    if ticker.isdigit():
            # 去除前导0，得到有效数字
            ticker_digits = ticker.lstrip('0') or '0'  # 如果全是0，保留一个0
            original_length = len(ticker)
            digits_length = len(ticker_digits)
            
            # 优先判断港股：如果原始是4-5位数字（包括前导0），优先识别为港股
            # 港股代码规则：yfinance需要去掉前导0，例如09988 -> 9988.HK，02525 -> 2525.HK
            if original_length == 4 or original_length == 5:
                # 原始4-5位数字，优先识别为港股（去掉前导0）
                normalized_hk = ticker_digits
                return f"{normalized_hk}.HK"
            
            # A股判断：如果原始是6位或补足到6位后符合A股规则
            if original_length == 6 or (original_length < 6 and digits_length <= 6):
                normalized_6 = ticker_digits.zfill(6)
                if normalized_6.startswith(('600', '601', '603', '688')):
                    return f"{normalized_6}.SS"  # 上海
                elif normalized_6.startswith(('000', '001', '002', '300')):
                    return f"{normalized_6}.SZ"  # 深圳
            
            # 其他情况：如果去0后是1-5位，可能是港股代码
            if digits_length >= 1 and digits_length <= 5:
                # 港股：使用去掉前导0的数字（yfinance格式）
                normalized_hk = ticker_digits
                return f"{normalized_hk}.HK"
    
    # 美股：默认不加后缀，或者已经是标准格式
    return ticker


def get_ticker_price(ticker, max_retries=3, retry_delay=2):
    """获取股票的当前价格，带重试机制"""
    normalized_ticker = normalize_ticker(ticker)
    print(f"原始代码: {ticker}, 标准化后: {normalized_ticker}")
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(normalized_ticker)

            # 尝试从info获取
            info = stock.info
            if info and len(info) >= 5:
                # 从info获取价格
                current_price = (info.get('currentPrice') or 
                               info.get('regularMarketPrice') or 
                               info.get('previousClose') or 0)
                if current_price > 0:
                    return current_price
            # 如果成功获取数据，跳出循环
            break
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"从info获取价格失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
            
            # 检查是否是速率限制错误（检查异常类型或消息）
            is_rate_limit = (isinstance(e, YFRateLimitError) or 
                           error_type == 'YFRateLimitError' or
                           "Too Many Requests" in error_msg or 
                           "Rate limited" in error_msg)
            
            # 检查是否是速率限制错误
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                # 其他错误或最后一次尝试失败
                if attempt == max_retries - 1:
                    print(f"获取价格失败，已重试 {max_retries} 次")
                break
    
    return None


def get_market_data(ticker, onlyHistoryData=False, startDate=None, max_retries=3, retry_delay=2, use_backup=True):
    """
    获取股票市场数据
    优先使用 Yahoo Finance，失败时自动切换到 Alpha Vantage（如果可用）
    
    参数:
        ticker: 股票代码
        onlyHistoryData: 是否只获取历史数据
        startDate: 开始日期
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        use_backup: 是否在失败时使用备用数据源（Alpha Vantage）
    """
    # 临时抑制yfinance的ERROR日志（ETF没有fundamentals数据时会报404，这是正常的）
    yfinance_logger = logging.getLogger('yfinance')
    original_level = yfinance_logger.level
    yfinance_logger.setLevel(logging.CRITICAL)  # 只显示CRITICAL级别的日志
    
    normalized_ticker = normalize_ticker(ticker)
    print(f"原始代码: {ticker}, 标准化后: {normalized_ticker}")
    
    yf_failed = False
    yf_error = None
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(normalized_ticker)

            if onlyHistoryData:
                try:
                    if startDate:
                        hist = stock.history(start=startDate, timeout=30)
                    else:
                        hist = stock.history(period="1y", timeout=30)
                except Exception as e:
                    error_msg = str(e)
                    error_type = type(e).__name__
                    print(f"获取历史数据失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                    
                    # 检查是否是速率限制错误（检查异常类型或消息）
                    is_rate_limit = (isinstance(e, YFRateLimitError) or 
                                   error_type == 'YFRateLimitError' or
                                   "Too Many Requests" in error_msg or 
                                   "Rate limited" in error_msg)
                    
                    if is_rate_limit:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1)  # 递增等待时间
                            print(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                            continue
                        else:
                            # 最后一次尝试也失败，标记失败并跳出循环，让备用数据源处理
                            yf_failed = True
                            yf_error = e
                            print(f"Yahoo Finance 所有重试均失败，将尝试备用数据源...")
                            break
                    else:
                        # 非速率限制错误，直接返回空数据
                        hist = pd.DataFrame()

                if not hist.empty:
                    history_dates = hist.index.strftime('%Y-%m-%d').tolist()
                    history_prices = hist['Close'].tolist()
                else:
                    from datetime import datetime
                    history_dates = [datetime.now().strftime('%Y-%m-%d')]
                    history_prices = []
                
                data = {
                    "history_dates": history_dates,
                    "history_prices": [float(p) for p in history_prices],
                }
                # 恢复yfinance日志级别
                yfinance_logger.setLevel(original_level)
                return data
            
            # 尝试获取信息，设置超时
            try:
                info = stock.info
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                print(f"获取股票信息失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                
                # 检查是否是速率限制错误（检查异常类型或消息）
                is_rate_limit = (isinstance(e, YFRateLimitError) or 
                               error_type == 'YFRateLimitError' or
                               "Too Many Requests" in error_msg or 
                               "Rate limited" in error_msg)
                
                if is_rate_limit:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 最后一次尝试也失败，标记失败并跳出循环，让备用数据源处理
                        yf_failed = True
                        yf_error = e
                        print(f"Yahoo Finance 所有重试均失败，将尝试备用数据源...")
                        break
                else:
                    info = {}
            
            # 尝试获取历史数据
            try:
                if startDate:
                    hist = stock.history(start=startDate, timeout=30)
                else:
                    hist = stock.history(period="1y", timeout=30)
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                print(f"获取历史数据失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                
                # 检查是否是速率限制错误（检查异常类型或消息）
                is_rate_limit = (isinstance(e, YFRateLimitError) or 
                               error_type == 'YFRateLimitError' or
                               "Too Many Requests" in error_msg or 
                               "Rate limited" in error_msg)
                
                if is_rate_limit:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 最后一次尝试也失败，标记失败并跳出循环，让备用数据源处理
                        yf_failed = True
                        yf_error = e
                        print(f"Yahoo Finance 所有重试均失败，将尝试备用数据源...")
                        break
                else:
                    hist = pd.DataFrame()
            
            # 如果成功获取数据，继续处理（不break，继续执行后面的数据处理逻辑）
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            # 检查是否是速率限制错误（检查异常类型或消息）
            is_rate_limit = (isinstance(e, YFRateLimitError) or 
                           error_type == 'YFRateLimitError' or
                           "Too Many Requests" in error_msg or 
                           "Rate limited" in error_msg)
            
            # 如果是速率限制错误且还有重试机会
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                # 最后一次尝试失败或其他错误，标记失败并跳出循环
                yf_failed = True
                yf_error = e
                if is_rate_limit:
                    print(f"Yahoo Finance 所有重试均失败，将尝试备用数据源...")
                else:
                    print(f"Yahoo Finance 失败: {error_msg}，将尝试备用数据源...")
                break
        
        # 如果成功执行到这里，说明数据获取成功，开始处理数据
        # 如果info为空或数据不足，尝试其他方式获取价格
        if not info or len(info) < 5:
            # 尝试快速获取
            try:
                fast_info = stock.fast_info
                if hasattr(fast_info, 'last_price') and fast_info.last_price:
                    current_price = fast_info.last_price
                elif not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    return None
            except:
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    # 恢复yfinance日志级别
                    yfinance_logger.setLevel(original_level)
                    return None
        else:
            # 从info或hist获取价格
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose') or 0)
            
            if current_price == 0 and not hist.empty:
                current_price = hist['Close'].iloc[-1]
            
            if current_price == 0:
                # 恢复yfinance日志级别
                yfinance_logger.setLevel(original_level)
                return None

        # 计算技术指标（如果有足够的历史数据）
        if not hist.empty and len(hist) >= 50:
            ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        else:
            ma50 = current_price
        
        if not hist.empty and len(hist) >= 200:
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        else:
            ma200 = current_price
        
        # 处理可能缺失的字段，使用安全的默认值
        pe_ratio = info.get('trailingPE') or info.get('forwardPE') or 0
        forward_pe = info.get('forwardPE') or 0
        peg_ratio = info.get('pegRatio') or 0
        rev_growth = info.get('revenueGrowth') or 0
        profit_margin = info.get('profitMargins') or 0
        
        # 确保数值类型正确
        try:
            pe_ratio = float(pe_ratio) if pe_ratio else 0
            forward_pe = float(forward_pe) if forward_pe else 0
            peg_ratio = float(peg_ratio) if peg_ratio else 0
            rev_growth = float(rev_growth) if rev_growth else 0
            profit_margin = float(profit_margin) if profit_margin else 0
        except (ValueError, TypeError):
            pe_ratio = forward_pe = peg_ratio = rev_growth = profit_margin = 0
        
        # 处理历史数据
        if not hist.empty:
            history_dates = hist.index.strftime('%Y-%m-%d').tolist()
            history_prices = hist['Close'].dropna().tolist()
            
            # 检测成交量异常（最近5天平均成交量 vs 过去30天平均成交量）
            if 'Volume' in hist.columns and len(hist) >= 30:
                recent_volume_avg = hist['Volume'].tail(5).mean()
                historical_volume_avg = hist['Volume'].tail(30).mean()
                if historical_volume_avg > 0:
                    volume_ratio = recent_volume_avg / historical_volume_avg
                    volume_anomaly = {
                        'ratio': float(volume_ratio),
                        'is_anomaly': bool(volume_ratio > 2.0 or volume_ratio < 0.3),  # 超过2倍或低于30%视为异常
                        'recent_avg': float(recent_volume_avg),
                        'historical_avg': float(historical_volume_avg)
                    }
                else:
                    volume_anomaly = None
            else:
                volume_anomaly = None
        else:
            # 如果没有历史数据，至少提供一个当前价格点
            from datetime import datetime
            history_dates = [datetime.now().strftime('%Y-%m-%d')]
            history_prices = [current_price]
            volume_anomaly = None
        
        # 获取52周高低价
        week52_high = (info.get('fiftyTwoWeekHigh') or 
                       info.get('52WeekHigh') or 
                       (hist['High'].max() if not hist.empty else current_price))
        week52_low = (info.get('fiftyTwoWeekLow') or 
                     info.get('52WeekLow') or 
                     (hist['Low'].min() if not hist.empty else current_price))
        
        # 确保价格数据有效
        if week52_high < current_price:
            week52_high = current_price * 1.2
        if week52_low > current_price:
            week52_low = current_price * 0.8
        
        # 获取财报日期（如果有）
        earnings_dates = []
        try:
            if hasattr(stock, 'calendar') and stock.calendar is not None:
                calendar = stock.calendar
                if calendar is not None and len(calendar) > 0:
                    # 获取最近的财报日期
                    if 'Earnings Date' in calendar:
                        earnings_dates = [d.strftime('%Y-%m-%d') for d in calendar['Earnings Date']]
        except:
            pass
        
        # 如果没有从calendar获取，尝试从info获取
        if not earnings_dates:
            try:
                if 'earningsTimestamp' in info and info['earningsTimestamp']:
                    if isinstance(info['earningsTimestamp'], list):
                        earnings_dates = [d.strftime('%Y-%m-%d') for d in info['earningsTimestamp']]
            except:
                pass
            
        # 获取IPO与解禁监控数据
        lockup_data = get_ipo_lockup_data(info, normalized_ticker)
        
        # 获取市值（如果有）
        market_cap = info.get('marketCap') or info.get('totalAssets') or 0
        try:
            market_cap = float(market_cap) if market_cap else 0
        except (ValueError, TypeError):
            market_cap = 0

        # 货币代码 → 货币符号映射
        currency_map = {
            'USD': '$',
            'CNY': '¥',
            'HKD': 'HK$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'KRW': '₩',
            'INR': '₹',
            'AUD': 'A$',
            'CAD': 'C$',
            'SGD': 'S$',
            'TWD': 'NT$',
        }
        
        # 根据normalized_ticker后缀判断货币代码
        if normalized_ticker.endswith('.HK'):
            currency_code = 'HKD'
        elif normalized_ticker.endswith('.SS'):
            currency_code = 'CNY'
        elif normalized_ticker.endswith('.SZ'):
            currency_code = 'CNY'
        else:
            # 默认美股
            currency_code = 'USD'
        
        currency_symbol = currency_map.get(currency_code, '$')  # 未映射的保持原代码
        
        # 计算ATR（用于动态止损）
        atr_value = None
        beta = None
        if not hist.empty and len(hist) >= 15:  # 至少需要15天数据计算ATR
            atr_value = calculate_atr(hist, period=14)
            # 尝试获取Beta值（用于调整ATR倍数）
            try:
                beta = info.get('beta')
                if beta:
                    beta = float(beta)
            except (ValueError, TypeError):
                beta = None
        
        # 获取公司名称
        company_name = info.get('longName') or info.get('shortName') or info.get('name') or normalized_ticker
        
        # 获取公司业务描述
        business_summary = info.get('longBusinessSummary') or info.get('businessSummary') or ''
        
        # 获取公司最新新闻（最多5条）
        company_news = []
        try:
            news_list = stock.news
            if news_list and len(news_list) > 0:
                # 只取最近5条新闻
                for news_item in news_list[:5]:
                    if isinstance(news_item, dict):
                        # yfinance的新闻数据结构是 {'id': ..., 'content': {...}}
                        # title在content字段中
                        content = news_item.get('content', {})
                        if isinstance(content, dict):
                            news_title = content.get('title') or content.get('headline') or ''
                            news_publisher = content.get('publisher') or content.get('provider', {}).get('displayName', '') if isinstance(content.get('provider'), dict) else ''
                            news_time = content.get('pubDate') or content.get('providerPublishTime') or content.get('datetime') or 0
                            news_link = content.get('canonicalUrl') or content.get('link') or content.get('url') or ''
                        else:
                            # 如果没有content字段，直接尝试从news_item获取
                            news_title = news_item.get('title') or news_item.get('headline') or ''
                            news_publisher = news_item.get('publisher') or news_item.get('source') or ''
                            news_time = news_item.get('pubDate') or news_item.get('providerPublishTime') or news_item.get('datetime') or 0
                            news_link = news_item.get('link') or news_item.get('url') or ''
                    else:
                        # 如果是对象，尝试访问属性
                        news_title = getattr(news_item, 'title', None) or getattr(news_item, 'headline', None) or ''
                        news_publisher = getattr(news_item, 'publisher', None) or getattr(news_item, 'source', None) or ''
                        news_time = getattr(news_item, 'pubDate', None) or getattr(news_item, 'providerPublishTime', None) or getattr(news_item, 'datetime', None) or 0
                        news_link = getattr(news_item, 'link', None) or getattr(news_item, 'url', None) or ''
                    
                    if news_title and str(news_title).strip():
                        company_news.append({
                            'title': str(news_title).strip(),
                            'publisher': str(news_publisher).strip() if news_publisher else '',
                            'time': news_time,
                            'link': str(news_link).strip() if news_link else ''
                        })
        except Exception as e:
            # 捕获所有新闻获取错误（包括SSL错误、网络错误等），不影响主流程
            error_msg = str(e)
            error_type = type(e).__name__
            # 如果是SSL错误或网络错误，只记录警告，不抛出异常
            if 'SSL' in error_msg or 'TLS' in error_msg or 'curl' in error_msg.lower() or 'network' in error_msg.lower() or 'SSLError' in error_type:
                print(f"获取新闻时遇到网络/SSL错误（不影响主流程）: {error_type}")
            else:
                print(f"获取公司新闻失败: {error_type}: {error_msg[:100]}")
            # 不抛出异常，继续执行主流程
        
        # 获取行业信息，如果缺失则尝试推断
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        
        # 如果行业信息缺失，尝试根据公司名称推断
        if sector == 'Unknown' or industry == 'Unknown' or not sector or not industry:
            inferred_sector, inferred_industry = infer_industry_from_name(company_name, normalized_ticker)
            if inferred_sector:
                sector = inferred_sector
            if inferred_industry:
                industry = inferred_industry
        
        # 构建基础数据
        data = {
            "symbol": normalized_ticker,
            "currency_symbol": currency_symbol,
            "original_symbol": ticker,
            "name": company_name,
            "sector": sector,
            "industry": industry,
            "business_summary": business_summary,  # 公司业务描述
            "company_news": company_news,  # 公司最新新闻
            "price": float(current_price),
            "week52_high": float(week52_high),
            "week52_low": float(week52_low),
            "pe": float(pe_ratio),
            "forward_pe": float(forward_pe),
            "peg": float(peg_ratio),
            "growth": float(rev_growth), # 小数形式
            "margin": float(profit_margin),
            "ma50": float(ma50),
            "ma200": float(ma200),
            "market_cap": market_cap,  # 市值（美元）
            "history_dates": history_dates,
            "history_prices": [float(p) for p in history_prices],
            "volume_anomaly": volume_anomaly,
            "earnings_dates": earnings_dates[:2] if earnings_dates else [],  # 只保留最近2个财报日期
            "lockup_data": lockup_data,  # IPO与解禁监控数据
            "atr": atr_value,  # ATR值，用于动态止损
            "beta": beta  # Beta值，用于调整ATR倍数
        }
        
        # 检查是否为ETF或基金
        is_fund, fund_type = is_etf_or_fund(data)
        data['is_etf_or_fund'] = is_fund
        data['fund_type'] = fund_type if is_fund else None
        
        # 恢复yfinance日志级别
        yfinance_logger.setLevel(original_level)
        
        # 成功处理完所有数据，返回结果
        return data
    
    # 恢复yfinance日志级别（如果提前返回）
    yfinance_logger.setLevel(original_level)
    
    # 如果 Yahoo Finance 失败，尝试使用备用数据源
    backup_error_detail = None
    if yf_failed and use_backup:
        try:
            from alpha_vantage_data import get_market_data_from_av, is_av_available
            
            if is_av_available():
                print(f"Yahoo Finance 失败，尝试使用 Alpha Vantage 作为备用数据源...")
                try:
                    backup_data = get_market_data_from_av(ticker, only_history=onlyHistoryData, start_date=startDate)
                    if backup_data:
                        print("✅ 成功从 Alpha Vantage 获取数据")
                        # 标记数据来源
                        backup_data['data_source'] = 'Alpha Vantage (备用)'
                        return backup_data
                except Exception as backup_error:
                    error_msg = str(backup_error)
                    print(f"❌ Alpha Vantage 备用数据源也失败: {error_msg}")
                    # 保存错误详情，用于后续错误报告
                    backup_error_detail = error_msg
                    # 如果 Alpha Vantage 是因为不支持该市场而失败，不抛出错误
                    if "仅支持美股" not in error_msg and "仅支持" not in error_msg:
                        # 对于其他错误（如速率限制），保存错误信息
                        pass
            else:
                print("⚠️ Alpha Vantage 不可用（未安装或未配置 API Key）")
                backup_error_detail = "Alpha Vantage 不可用（未安装或未配置 API Key）"
        except ImportError:
            print("⚠️ Alpha Vantage 模块未安装，无法使用备用数据源")
            backup_error_detail = "Alpha Vantage 模块未安装"
        except Exception as e:
            print(f"⚠️ 尝试使用备用数据源时出错: {e}")
            backup_error_detail = str(e)
    
    # 如果所有尝试都失败，抛出异常以便 app.py 能够捕获并返回详细错误
    if yf_failed:
        # 构建详细的错误信息
        error_parts = []
        if yf_error:
            error_parts.append(f"Yahoo Finance: {str(yf_error)}")
        if backup_error_detail:
            error_parts.append(f"Alpha Vantage (备用): {backup_error_detail}")
        
        if error_parts:
            combined_error = "数据获取失败：\n" + "\n".join(f"- {part}" for part in error_parts)
            # 检查是否是速率限制错误
            # 检查错误信息中是否包含速率限制的关键词
            has_rate_limit = False
            rate_limit_keywords = ["速率限制", "Too Many Requests", "Rate limited", "API call frequency", 
                                   "Thank you for using Alpha Vantage", "rate limit", "请求过于频繁"]
            
            for keyword in rate_limit_keywords:
                if keyword in combined_error:
                    has_rate_limit = True
                    break
            
            if has_rate_limit:
                # 提供更详细和实用的错误信息
                error_message = """⚠️ 数据源暂时繁忙

所有数据源（Yahoo Finance 和 Alpha Vantage）当前都遇到速率限制。

速率限制说明：
• Yahoo Finance：免费 API 有严格的速率限制，可能需要在 15-30 分钟后才能恢复
• Alpha Vantage 免费版：每分钟限制 5 次请求，每天限制 500 次请求

如果已经等待很久仍然报错，可能的原因：
1. 今日查询次数已达到上限（特别是 Alpha Vantage 每天 500 次）
2. IP 地址被暂时限制（Yahoo Finance 可能对频繁请求的 IP 进行临时封禁）
3. 数据源正在进行维护

建议操作：
• 等待 30-60 分钟后再试（Yahoo Finance 可能需要更长时间）
• 如果急需数据，可以尝试使用 VPN 更换 IP 地址
• 避免在短时间内多次查询
• 可以尝试查询不同的股票代码（某些代码可能不会触发限制）
• 如果频繁遇到此问题，建议使用付费的数据源 API

注意：这是免费 API 的正常限制，不是系统错误。"""
                raise Exception(error_message)
            else:
                raise Exception(combined_error)
        else:
            raise Exception(f"无法获取股票 {ticker} 的数据：所有数据源均失败")
    
    # 如果所有尝试都失败，返回None（正常情况下不应该到达这里）
    return None


def get_fed_meeting_dates():
    """
    获取美联储利率决议日期
    返回未来3个月内的FOMC会议日期
    """
    # 2025年FOMC会议日期（根据美联储官方日程）
    fed_meetings_2025 = [
        datetime(2025, 1, 28),  # 1月28-29日
        datetime(2025, 3, 18),  # 3月18-19日（含点阵图）
        datetime(2025, 5, 6),   # 5月6-7日
        datetime(2025, 6, 17),  # 6月17-18日（含点阵图）
        datetime(2025, 7, 29),  # 7月29-30日
        datetime(2025, 9, 16),  # 9月16-17日（含点阵图）
        datetime(2025, 10, 28), # 10月28-29日
        datetime(2025, 12, 9), # 12月9-10日（含点阵图）
    ]
    
    # 2026年部分日期（如果需要）
    fed_meetings_2026 = [
        datetime(2026, 1, 28),
        datetime(2026, 3, 18),
    ]
    
    all_meetings = fed_meetings_2025 + fed_meetings_2026
    today = datetime.now().date()
    
    # 筛选未来90天内的会议
    upcoming_meetings = []
    for meeting_date in all_meetings:
        meeting_date_only = meeting_date.date()
        days_until = (meeting_date_only - today).days
        if 0 <= days_until <= 90:  # 未来90天内
            upcoming_meetings.append({
                'date': meeting_date_only.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'has_dot_plot': bool(meeting_date.month in [3, 6, 9, 12])  # 季度会议含点阵图
            })
    
    return sorted(upcoming_meetings, key=lambda x: x['days_until'])[:3]  # 返回最近3个


def get_cpi_release_dates():
    """
    获取美国CPI发布日期
    CPI通常在每月中旬（10-15日）发布前一个月的数据
    """
    today = datetime.now().date()
    cpi_dates = []
    
    # 计算未来3个月的CPI发布日期
    for i in range(1, 4):
        # 下个月的数据在这个月发布
        target_month = today + relativedelta(months=i)
        # CPI通常在每月10-15日之间发布，我们假设是12日
        cpi_date = datetime(target_month.year, target_month.month, 12).date()
        
        # 如果12日是周末，调整到下一个工作日
        while cpi_date.weekday() >= 5:  # 周六或周日
            cpi_date += timedelta(days=1)
        
        days_until = (cpi_date - today).days
        if days_until >= 0:
            cpi_dates.append({
                'date': cpi_date.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'data_month': (target_month - relativedelta(months=1)).strftime('%Y年%m月'),
                'country': 'US'
            })
    
    return cpi_dates[:3]  # 返回最近3个


def get_china_economic_events():
    """
    获取中国重要经济事件日期
    包括：央行货币政策会议、CPI/PPI发布、GDP发布、PMI发布
    """
    today = datetime.now().date()
    events = []
    
    # 1. 中国央行货币政策会议（通常每季度一次，1/4/7/10月）
    current_year = today.year
    pboc_meetings = [
        datetime(current_year, 1, 20).date(),  # 通常在一月下旬
        datetime(current_year, 4, 20).date(),  # 通常在四月中旬
        datetime(current_year, 7, 20).date(),  # 通常在七月中旬
        datetime(current_year, 10, 20).date(), # 通常在十月中旬
        datetime(current_year + 1, 1, 20).date()  # 下一年
    ]
    
    for meeting_date in pboc_meetings:
        days_until = (meeting_date - today).days
        if 0 <= days_until <= 90:
            events.append({
                'date': meeting_date.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'type': '央行货币政策会议',
                'country': 'CN'
            })
    
    # 2. 中国CPI/PPI发布（通常在每月9-10日发布上月数据）
    for i in range(1, 4):
        target_month = today + relativedelta(months=i)
        # CPI通常在每月9-10日发布
        cpi_date = datetime(target_month.year, target_month.month, 10).date()
        # 如果是周末，调整到下一个工作日
        while cpi_date.weekday() >= 5:
            cpi_date += timedelta(days=1)
        
        days_until = (cpi_date - today).days
        if days_until >= 0:
            events.append({
                'date': cpi_date.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'type': 'CPI/PPI发布',
                'country': 'CN',
                'data_month': (target_month - relativedelta(months=1)).strftime('%Y年%m月')
            })
    
    # 3. 中国GDP发布（季度数据，通常在季后15-20日发布）
    # Q1在4月中旬，Q2在7月中旬，Q3在10月中旬，Q4在次年1月中旬
    gdp_releases = [
        datetime(current_year, 4, 18).date(),   # Q1数据
        datetime(current_year, 7, 18).date(),   # Q2数据
        datetime(current_year, 10, 18).date(),  # Q3数据
        datetime(current_year + 1, 1, 18).date() # Q4数据
    ]
    
    for gdp_date in gdp_releases:
        days_until = (gdp_date - today).days
        if 0 <= days_until <= 90:
            quarter = 'Q1' if gdp_date.month == 4 else 'Q2' if gdp_date.month == 7 else 'Q3' if gdp_date.month == 10 else 'Q4'
            events.append({
                'date': gdp_date.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'type': 'GDP发布',
                'country': 'CN',
                'quarter': quarter
            })
    
    # 4. 中国PMI发布（每月最后一天或次月1日发布上月数据）
    for i in range(1, 4):
        target_month = today + relativedelta(months=i)
        # PMI通常在每月最后一天或次月1日发布
        pmi_date = datetime(target_month.year, target_month.month, 1).date()
        # 如果是周末，调整到下一个工作日
        while pmi_date.weekday() >= 5:
            pmi_date += timedelta(days=1)
        
        days_until = (pmi_date - today).days
        if days_until >= 0:
            events.append({
                'date': pmi_date.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'type': 'PMI发布',
                'country': 'CN',
                'data_month': (target_month - relativedelta(months=1)).strftime('%Y年%m月')
            })
    
    return sorted(events, key=lambda x: x['days_until'])[:10]  # 返回最近10个事件


def get_options_expiration_dates():
    """
    获取期权到期日（交割日）
    美股期权规则：
    - 月度期权：每月第三个星期五
    - 季度期权：3月、6月、9月、12月的第三个星期五（四重到期日，Quadruple Witching）
    - 周度期权：每周五（但重要性较低，这里主要关注月度）
    
    返回未来3个月内的期权到期日
    """
    today = datetime.now().date()
    expiration_dates = []
    
    # 计算未来3个月的期权到期日
    for i in range(0, 4):  # 包括当前月
        target_month = today + relativedelta(months=i)
        year = target_month.year
        month = target_month.month
        
        # 找到该月第一个星期五
        first_day = datetime(year, month, 1).date()
        # 计算到第一个星期五需要多少天（星期五是4）
        days_to_first_friday = (4 - first_day.weekday()) % 7
        if days_to_first_friday == 0 and first_day.weekday() != 4:
            days_to_first_friday = 7
        
        first_friday = first_day + timedelta(days=days_to_first_friday)
        
        # 第三个星期五 = 第一个星期五 + 14天
        third_friday = first_friday + timedelta(days=14)
        
        # 如果第三个星期五已经过去，计算下个月的
        if third_friday < today and i == 0:
            # 计算下个月的
            next_month = today + relativedelta(months=1)
            year = next_month.year
            month = next_month.month
            first_day = datetime(year, month, 1).date()
            days_to_first_friday = (4 - first_day.weekday()) % 7
            if days_to_first_friday == 0 and first_day.weekday() != 4:
                days_to_first_friday = 7
            first_friday = first_day + timedelta(days=days_to_first_friday)
            third_friday = first_friday + timedelta(days=14)
        
        days_until = (third_friday - today).days
        
        # 只添加未来的日期
        if days_until >= 0:
            # 判断是否为季度到期日（四重到期日）
            is_quadruple_witching = month in [3, 6, 9, 12]
            
            expiration_dates.append({
                'date': third_friday.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'month': month,
                'is_quadruple_witching': is_quadruple_witching,
                'type': '四重到期日（季度）' if is_quadruple_witching else '月度到期日'
            })
    
    # 去重并排序
    seen_dates = set()
    unique_dates = []
    for exp_date in expiration_dates:
        if exp_date['date'] not in seen_dates:
            seen_dates.add(exp_date['date'])
            unique_dates.append(exp_date)
    
    return sorted(unique_dates, key=lambda x: x['days_until'])[:3]  # 返回最近3个


def get_market_warnings(macro_data, options_data, data):
    """
    生成市场预警信息
    提前提醒即将发生的风险和重要事件
    返回预警列表，每个预警包含：级别、类型、消息、距离天数（如果是事件）
    """
    warnings = []
    
    # 1. VIX预警（提前预警，而不是等它已经很高）
    if options_data.get('vix') is not None:
        vix = options_data['vix']
        vix_change = options_data.get('vix_change', 0)
        
        if vix >= 30:
            warnings.append({
                'level': 'high',
                'type': 'vix',
                'message': f'VIX已处于高位({vix:.1f})，市场恐慌情绪严重',
                'urgency': 'immediate'
            })
        elif vix >= 25:
            warnings.append({
                'level': 'medium',
                'type': 'vix',
                'message': f'VIX接近危险区域({vix:.1f})，距离30仅差{30-vix:.1f}点，需密切关注',
                'urgency': 'soon'
            })
        elif vix >= 20 and vix_change > 5:
            warnings.append({
                'level': 'medium',
                'type': 'vix',
                'message': f'VIX快速上升({vix_change:.1f}%)，当前{vix:.1f}，可能继续攀升',
                'urgency': 'soon'
            })
        elif vix >= 20:
            warnings.append({
                'level': 'low',
                'type': 'vix',
                'message': f'VIX处于中等偏高水平({vix:.1f})，需保持警惕',
                'urgency': 'monitor'
            })
    
    # 2. Put/Call比率预警
    if options_data.get('put_call_ratio') is not None:
        pc_ratio = options_data['put_call_ratio']
        if pc_ratio >= 1.5:
            warnings.append({
                'level': 'high',
                'type': 'options',
                'message': f'Put/Call比率极高({pc_ratio:.2f})，看跌情绪强烈，存在负Gamma风险',
                'urgency': 'immediate'
            })
        elif pc_ratio >= 1.2:
            warnings.append({
                'level': 'medium',
                'type': 'options',
                'message': f'Put/Call比率偏高({pc_ratio:.2f})，接近危险区域，需警惕',
                'urgency': 'soon'
            })
    
    # 3. 美债收益率预警
    if macro_data.get('treasury_10y') is not None:
        treasury = macro_data['treasury_10y']
        treasury_change = macro_data.get('treasury_10y_change', 0)
        
        if treasury >= 5.0:
            warnings.append({
                'level': 'high',
                'type': 'macro',
                'message': f'10年美债收益率极高({treasury:.2f}%)，流动性严重收紧',
                'urgency': 'immediate'
            })
        elif treasury >= 4.5:
            warnings.append({
                'level': 'medium',
                'type': 'macro',
                'message': f'10年美债收益率偏高({treasury:.2f}%)，接近危险区域，流动性收紧',
                'urgency': 'soon'
            })
        elif treasury_change > 0.2:
            warnings.append({
                'level': 'medium',
                'type': 'macro',
                'message': f'10年美债收益率快速上升(+{treasury_change:.2f}%)，流动性收紧信号',
                'urgency': 'soon'
            })
    
    # 4. 黄金避险情绪预警
    if macro_data.get('gold_change') is not None:
        gold_change = macro_data['gold_change']
        if gold_change > 3:
            warnings.append({
                'level': 'high',
                'type': 'macro',
                'message': f'黄金大幅上涨({gold_change:.2f}%)，避险情绪强烈，可能预示地缘政治风险',
                'urgency': 'immediate'
            })
        elif gold_change > 1.5:
            warnings.append({
                'level': 'medium',
                'type': 'macro',
                'message': f'黄金明显上涨({gold_change:.2f}%)，避险情绪上升',
                'urgency': 'soon'
            })
    
    # 5. 美联储会议预警（提前提醒）
    if macro_data.get('fed_meetings'):
        for meeting in macro_data['fed_meetings']:
            days_until = meeting['days_until']
            if days_until <= 3:
                warnings.append({
                    'level': 'high',
                    'type': 'event',
                    'message': f'美联储利率决议将在{meeting["date"]}举行（{days_until}天后）{"，含点阵图" if meeting["has_dot_plot"] else ""}',
                    'urgency': 'immediate',
                    'event_date': meeting['date']
                })
            elif days_until <= 7:
                warnings.append({
                    'level': 'medium',
                    'type': 'event',
                    'message': f'美联储利率决议将在{meeting["date"]}举行（{days_until}天后）{"，含点阵图" if meeting["has_dot_plot"] else ""}，建议提前调整仓位',
                    'urgency': 'soon',
                    'event_date': meeting['date']
                })
            elif days_until <= 14:
                warnings.append({
                    'level': 'low',
                    'type': 'event',
                    'message': f'美联储利率决议将在{meeting["date"]}举行（{days_until}天后），建议关注',
                    'urgency': 'monitor',
                    'event_date': meeting['date']
                })
    
    # 6. 美国CPI发布预警
    if macro_data.get('cpi_releases'):
        for cpi in macro_data['cpi_releases']:
            if cpi.get('country') == 'US':  # 只处理美国CPI
                days_until = cpi['days_until']
                if days_until <= 3:
                    warnings.append({
                        'level': 'high',
                        'type': 'event',
                        'message': f'美国CPI数据将在{cpi["date"]}发布（{days_until}天后，{cpi["data_month"]}数据），市场波动可能加剧',
                        'urgency': 'immediate',
                        'event_date': cpi['date'],
                        'country': 'US'
                    })
                elif days_until <= 7:
                    warnings.append({
                        'level': 'medium',
                        'type': 'event',
                        'message': f'美国CPI数据将在{cpi["date"]}发布（{days_until}天后，{cpi["data_month"]}数据），建议关注',
                        'urgency': 'soon',
                        'event_date': cpi['date'],
                        'country': 'US'
                    })
    
    # 6.5 中国经济事件预警
    if macro_data.get('china_events'):
        for event in macro_data['china_events']:
            days_until = event['days_until']
            event_type = event.get('type', '经济事件')
            country = event.get('country', 'CN')
            
            if days_until <= 3:
                message = f'中国{event_type}将在{event["date"]}举行/发布（{days_until}天后）'
                if event.get('data_month'):
                    message += f'，{event["data_month"]}数据'
                elif event.get('quarter'):
                    message += f'，{event["quarter"]}数据'
                message += '，可能影响A股和港股市场'
                
                warnings.append({
                    'level': 'high',
                    'type': 'event',
                    'message': message,
                    'urgency': 'immediate',
                    'event_date': event['date'],
                    'country': country
                })
            elif days_until <= 7:
                message = f'中国{event_type}将在{event["date"]}举行/发布（{days_until}天后）'
                if event.get('data_month'):
                    message += f'，{event["data_month"]}数据'
                elif event.get('quarter'):
                    message += f'，{event["quarter"]}数据'
                message += '，建议关注'
                
                warnings.append({
                    'level': 'medium',
                    'type': 'event',
                    'message': message,
                    'urgency': 'soon',
                    'event_date': event['date'],
                    'country': country
                })
    
    # 7. 期权到期日（交割日）预警 - 市场级别风险
    # 期权到期日是市场级别的风险，会影响整个市场的波动性
    if macro_data.get('options_expirations'):
        for exp in macro_data['options_expirations']:
            days_until = exp['days_until']
            is_quadruple = exp.get('is_quadruple_witching', False)
            
            # 期权到期日会导致市场波动增加，这是市场级别的风险
            if days_until <= 1:
                # 当天或明天到期，市场波动风险最高
                warnings.append({
                    'level': 'high',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日，市场波动风险极高，做市商需要大量调整对冲头寸" if is_quadruple else " - 月度到期日，市场波动风险增加，做市商需要调整对冲"}',
                    'urgency': 'immediate',
                    'event_date': exp['date']
                })
            elif days_until <= 3:
                warnings.append({
                    'level': 'high',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日，市场波动风险高" if is_quadruple else " - 月度到期日，市场波动风险上升"}',
                    'urgency': 'immediate',
                    'event_date': exp['date']
                })
            elif days_until <= 7:
                warnings.append({
                    'level': 'medium',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日" if is_quadruple else " - 月度到期日"}，市场波动风险增加，建议降低仓位或保持观望',
                    'urgency': 'soon',
                    'event_date': exp['date']
                })
            elif days_until <= 14:
                warnings.append({
                    'level': 'low',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日" if is_quadruple else " - 月度到期日"}，市场波动风险上升，建议关注',
                    'urgency': 'monitor',
                    'event_date': exp['date']
                })
    
    # 8. 财报日期预警（个股级别）
    if data.get('earnings_dates'):
        for earnings_date in data['earnings_dates']:
            try:
                earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                today = datetime.now().date()
                days_until = (earnings_dt - today).days
                
                if 0 <= days_until <= 3:
                    warnings.append({
                        'level': 'high',
                        'type': 'event',
                        'message': f'财报将在{earnings_date}发布（{days_until}天后），波动可能加剧',
                        'urgency': 'immediate',
                        'event_date': earnings_date
                    })
                elif 0 <= days_until <= 7:
                    warnings.append({
                        'level': 'medium',
                        'type': 'event',
                        'message': f'财报将在{earnings_date}发布（{days_until}天后），建议关注',
                        'urgency': 'soon',
                        'event_date': earnings_date
                    })
            except:
                pass
    
    # 9. 成交量异常预警
    if data.get('volume_anomaly') and data['volume_anomaly'].get('is_anomaly'):
        ratio = data['volume_anomaly'].get('ratio', 1)
        if ratio > 3:
            warnings.append({
                'level': 'high',
                'type': 'technical',
                'message': f'成交量异常放大({ratio:.2f}倍)，可能存在重大消息或资金异动',
                'urgency': 'immediate'
            })
        elif ratio > 2:
            warnings.append({
                'level': 'medium',
                'type': 'technical',
                'message': f'成交量明显放大({ratio:.2f}倍)，需密切关注',
                'urgency': 'soon'
            })
    
    # 10. 地缘政治风险预警
    if macro_data.get('geopolitical_risk') is not None:
        gpr = macro_data['geopolitical_risk']
        if gpr >= 7:
            warnings.append({
                'level': 'high',
                'type': 'geopolitical',
                'message': f'地缘政治风险指数极高({gpr}/10)，市场避险情绪强烈，建议降低风险敞口',
                'urgency': 'immediate'
            })
        elif gpr >= 6:
            warnings.append({
                'level': 'medium',
                'type': 'geopolitical',
                'message': f'地缘政治风险指数偏高({gpr}/10)，需保持警惕',
                'urgency': 'soon'
            })
    
    # 10. Polymarket预测市场预警
    if macro_data.get('polymarket'):
        polymarket_data = macro_data['polymarket']
        
        # 检查关键事件
        if polymarket_data.get('key_events'):
            key_events = polymarket_data['key_events']
            
            # 检查是否有高流动性的负面事件
            negative_keywords = ['recession', 'crash', 'crisis', 'war', 'conflict', 'sanction', 'default', 'bankruptcy']
            high_liquidity_negative = []
            
            for event in key_events:
                question = event.get('question', '').lower()
                liquidity = event.get('liquidity', 0)
                
                if any(keyword in question for keyword in negative_keywords) and liquidity > 10000:
                    high_liquidity_negative.append(event)
            
            if len(high_liquidity_negative) > 0:
                # 按流动性排序，取最重要的
                high_liquidity_negative.sort(key=lambda x: x.get('liquidity', 0), reverse=True)
                top_event = high_liquidity_negative[0]
                
                warnings.append({
                    'level': 'high',
                    'type': 'polymarket',
                    'message': f'Polymarket预测市场显示重大风险事件：{top_event.get("question", "")[:50]}...（流动性：${top_event.get("liquidity", 0):,.0f}）',
                    'urgency': 'immediate'
                })
        
        # 检查经济预测
        if polymarket_data.get('economic_predictions'):
            econ_events = polymarket_data['economic_predictions']
            # 检查是否有高流动性的经济衰退预测
            recession_events = [e for e in econ_events if 'recession' in e.get('question', '').lower() and e.get('liquidity', 0) > 5000]
            if len(recession_events) > 0:
                warnings.append({
                    'level': 'medium',
                    'type': 'polymarket',
                    'message': f'Polymarket显示经济衰退预测市场活跃（{len(recession_events)}个相关市场），需关注经济风险',
                    'urgency': 'soon'
                })
        
        # 检查美联储政策预测
        if polymarket_data.get('fed_policy_predictions'):
            fed_events = polymarket_data['fed_policy_predictions']
            high_liquidity_fed = [e for e in fed_events if e.get('liquidity', 0) > 10000]
            if len(high_liquidity_fed) > 0:
                warnings.append({
                    'level': 'medium',
                    'type': 'polymarket',
                    'message': f'Polymarket显示美联储政策预测市场活跃（{len(high_liquidity_fed)}个高流动性市场），可能预示政策变化',
                    'urgency': 'monitor'
                })
    
    # 按紧急程度和级别排序
    urgency_order = {'immediate': 0, 'soon': 1, 'monitor': 2}
    level_order = {'high': 0, 'medium': 1, 'low': 2}
    
    warnings.sort(key=lambda x: (
        urgency_order.get(x.get('urgency', 'monitor'), 2),
        level_order.get(x.get('level', 'low'), 2)
    ))
    
    return warnings


def calculate_geopolitical_risk(macro_data, options_data):
    """
    计算地缘政治风险指数
    基于多个代理指标：黄金价格、VIX、美元指数等
    返回0-10分，分数越高表示地缘政治风险越高
    """
    risk_score = 5.0  # 基准分
    
    # 1. 黄金价格变化（权重40%）
    # 地缘政治风险上升时，黄金通常上涨
    if macro_data.get('gold_change') is not None:
        gold_change = macro_data['gold_change']
        if gold_change > 3:
            gold_risk = 8.0  # 大幅上涨，风险高
        elif gold_change > 1.5:
            gold_risk = 6.5  # 明显上涨
        elif gold_change > 0.5:
            gold_risk = 5.5  # 略有上涨
        elif gold_change < -2:
            gold_risk = 3.0  # 大幅下跌，风险偏好上升
        else:
            gold_risk = 5.0  # 中性
        risk_score = gold_risk * 0.4
    else:
        risk_score = 5.0 * 0.4
    
    # 2. VIX恐慌指数（权重30%）
    # VIX上升可能反映地缘政治担忧
    if options_data.get('vix') is not None:
        vix = options_data['vix']
        if vix > 30:
            vix_risk = 8.5  # 高恐慌
        elif vix > 25:
            vix_risk = 7.0
        elif vix > 20:
            vix_risk = 5.5
        elif vix < 15:
            vix_risk = 3.5  # 低恐慌
        else:
            vix_risk = 5.0
        risk_score += vix_risk * 0.3
    else:
        risk_score += 5.0 * 0.3
    
    # 3. 美元指数（权重20%）
    # 地缘政治风险上升时，美元可能走强（避险）
    if macro_data.get('dxy') is not None:
        dxy = macro_data['dxy']
        dxy_change = macro_data.get('dxy_change', 0)
        
        # 美元走强且快速上升可能反映避险需求
        if dxy > 105 and dxy_change > 1:
            dxy_risk = 7.5
        elif dxy > 105:
            dxy_risk = 6.0
        elif dxy < 95:
            dxy_risk = 4.0  # 弱势美元，风险偏好
        else:
            dxy_risk = 5.0
        risk_score += dxy_risk * 0.2
    else:
        risk_score += 5.0 * 0.2
    
    # 4. 原油价格波动（权重10%）
    # 地缘政治事件通常影响原油供应
    if macro_data.get('oil_change') is not None:
        oil_change = abs(macro_data['oil_change'])
        if oil_change > 5:
            oil_risk = 7.0  # 大幅波动
        elif oil_change > 3:
            oil_risk = 6.0
        else:
            oil_risk = 5.0
        risk_score += oil_risk * 0.1
    else:
        risk_score += 5.0 * 0.1
    
    # 确保在0-10范围内
    risk_score = max(0, min(10, risk_score))
    
    return round(risk_score, 1)


def get_macro_market_data():
    """
    获取宏观经济和市场情绪指标
    包括：美债收益率、美元指数、黄金、原油等
    这些指标反映市场流动性、避险情绪和宏观经济环境
    """
    macro_data = {
        'treasury_10y': None,  # 10年期美债收益率
        'treasury_10y_change': None,
        'dxy': None,  # 美元指数
        'dxy_change': None,
        'gold': None,  # 黄金价格
        'gold_change': None,
        'oil': None,  # 原油价格
        'oil_change': None,
        'volume_anomaly': None,  # 成交量异常（需要结合个股数据）
        'fed_meetings': [],  # 美联储会议日期
        'cpi_releases': [],  # 美国CPI发布日期
        'china_events': [],  # 中国经济事件（央行会议、CPI/PPI、GDP、PMI）
        'other_events': [],  # 其他国家的重要经济事件（后续可扩展）
        'options_expirations': [],  # 期权到期日（交割日）
        'geopolitical_risk': None,  # 地缘政治风险指数
    }
    
    try:
        # 1. 10年期美债收益率 (^TNX) - 反映市场对利率和通胀的预期
        try:
            tnx = yf.Ticker('^TNX')
            tnx_hist = tnx.history(period='5d', timeout=10)
            if not tnx_hist.empty and len(tnx_hist) >= 2:
                treasury_current = float(tnx_hist['Close'].iloc[-1])
                treasury_prev = float(tnx_hist['Close'].iloc[-2])
                treasury_change = treasury_current - treasury_prev
                macro_data['treasury_10y'] = treasury_current
                macro_data['treasury_10y_change'] = treasury_change
        except Exception as e:
            print(f"获取美债收益率失败: {e}")
        
        # 2. 美元指数 (DX-Y.NYB 或 ^DXY) - 反映美元强弱，影响全球流动性
        try:
            dxy = yf.Ticker('DX-Y.NYB')
            dxy_hist = dxy.history(period='5d', timeout=10)
            if dxy_hist.empty:
                # 尝试备用代码
                dxy = yf.Ticker('^DXY')
                dxy_hist = dxy.history(period='5d', timeout=10)
            
            if not dxy_hist.empty and len(dxy_hist) >= 2:
                dxy_current = float(dxy_hist['Close'].iloc[-1])
                dxy_prev = float(dxy_hist['Close'].iloc[-2])
                dxy_change = ((dxy_current - dxy_prev) / dxy_prev) * 100
                macro_data['dxy'] = dxy_current
                macro_data['dxy_change'] = dxy_change
        except Exception as e:
            print(f"获取美元指数失败: {e}")
        
        # 3. 黄金价格 (GC=F) - 避险情绪指标
        try:
            gold = yf.Ticker('GC=F')
            gold_hist = gold.history(period='5d', timeout=10)
            if not gold_hist.empty and len(gold_hist) >= 2:
                gold_current = float(gold_hist['Close'].iloc[-1])
                gold_prev = float(gold_hist['Close'].iloc[-2])
                gold_change = ((gold_current - gold_prev) / gold_prev) * 100
                macro_data['gold'] = gold_current
                macro_data['gold_change'] = gold_change
        except Exception as e:
            print(f"获取黄金价格失败: {e}")
        
        # 4. 原油价格 (CL=F) - 通胀和经济增长预期
        try:
            oil = yf.Ticker('CL=F')
            oil_hist = oil.history(period='5d', timeout=10)
            if not oil_hist.empty and len(oil_hist) >= 2:
                oil_current = float(oil_hist['Close'].iloc[-1])
                oil_prev = float(oil_hist['Close'].iloc[-2])
                oil_change = ((oil_current - oil_prev) / oil_prev) * 100
                macro_data['oil'] = oil_current
                macro_data['oil_change'] = oil_change
        except Exception as e:
            print(f"获取原油价格失败: {e}")
        
        # 5. 获取美联储会议日期
        try:
            macro_data['fed_meetings'] = get_fed_meeting_dates()
        except Exception as e:
            print(f"获取美联储会议日期失败: {e}")
        
        # 6. 获取CPI发布日期
        try:
            macro_data['cpi_releases'] = get_cpi_release_dates()
        except Exception as e:
            print(f"获取CPI发布日期失败: {e}")
        
        # 7. 获取期权到期日（交割日）
        try:
            macro_data['options_expirations'] = get_options_expiration_dates()
        except Exception as e:
            print(f"获取期权到期日失败: {e}")
        
        # 8. 获取中国经济事件
        try:
            macro_data['china_events'] = get_china_economic_events()
        except Exception as e:
            print(f"获取中国经济事件失败: {e}")
            
    except Exception as e:
        print(f"获取宏观经济数据时出错: {e}")
    
    return macro_data


def get_polymarket_data():
    """
    获取Polymarket预测市场的关键数据
    Polymarket是一个预测市场平台，可以反映市场对重大事件的预期
    返回关键预测市场数据，如选举、经济政策、市场事件等
    """
    polymarket_data = {
        'election_predictions': [],  # 选举预测
        'economic_predictions': [],  # 经济政策预测
        'market_event_predictions': [],  # 市场事件预测
        'geopolitical_predictions': [],  # 地缘政治预测
        'fed_policy_predictions': [],  # 美联储政策预测
        'overall_sentiment': None,  # 综合市场情绪（基于预测市场）
        'key_events': []  # 关键事件列表
    }
    
    try:
        # Polymarket公共API端点
        # 注意：这是公共API，可能需要根据实际API文档调整
        base_url = "https://clob.polymarket.com"
        
        # 尝试获取活跃市场数据
        try:
            # 获取市场列表（这里使用Polymarket的GraphQL API或REST API）
            # 由于Polymarket API可能有变化，我们使用一个通用的方法
            markets_url = f"{base_url}/markets"
            
            # 定义我们关注的关键市场类别
            key_categories = [
                'election',  # 选举
                'economics',  # 经济
                'policy',  # 政策
                'geopolitics',  # 地缘政治
                'fed',  # 美联储
                'crypto',  # 加密货币（可能影响市场）
                'regulation'  # 监管
            ]
            
            # 尝试从Polymarket获取数据
            # 注意：实际API可能需要认证或使用不同的端点
            # 这里提供一个框架，实际使用时需要根据Polymarket的最新API文档调整
            
            # 方法1：尝试使用公共GraphQL端点（如果可用）
            graphql_url = "https://clob.polymarket.com/graphql"
            
            # 查询关键市场
            query = """
            {
                markets(where: {active: true, closed: false}, orderBy: volume, orderDirection: desc, first: 20) {
                    id
                    question
                    conditionId
                    outcomes
                    volume
                    liquidity
                    endDate
                    image
                    active
                    closed
                    category
                }
            }
            """
            
            try:
                response = requests.post(
                    graphql_url,
                    json={'query': query},
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'markets' in data['data']:
                        markets = data['data']['markets']
                        
                        # 分类处理市场数据
                        for market in markets:
                            question = market.get('question', '').lower()
                            category = market.get('category', '').lower()
                            volume = float(market.get('volume', 0))
                            liquidity = float(market.get('liquidity', 0))
                            
                            # 只处理有足够流动性的市场
                            if liquidity < 1000:  # 流动性阈值
                                continue
                            
                            market_info = {
                                'question': market.get('question', ''),
                                'condition_id': market.get('conditionId', ''),
                                'volume': volume,
                                'liquidity': liquidity,
                                'end_date': market.get('endDate', ''),
                                'category': category
                            }
                            
                            # 根据关键词分类
                            if any(keyword in question or keyword in category for keyword in ['election', 'president', 'senate', 'house', 'vote']):
                                polymarket_data['election_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['gdp', 'inflation', 'cpi', 'unemployment', 'recession', 'economic']):
                                polymarket_data['economic_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['fed', 'federal reserve', 'interest rate', 'fomc', 'rate cut', 'rate hike']):
                                polymarket_data['fed_policy_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['war', 'conflict', 'sanction', 'trade', 'geopolitical', 'russia', 'china', 'iran']):
                                polymarket_data['geopolitical_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['market', 'crash', 'rally', 'sp500', 'dow', 'nasdaq']):
                                polymarket_data['market_event_predictions'].append(market_info)
                            
                            # 添加到关键事件列表（按流动性排序）
                            if liquidity > 5000:
                                polymarket_data['key_events'].append(market_info)
                        
                        # 按流动性排序
                        polymarket_data['key_events'].sort(key=lambda x: x.get('liquidity', 0), reverse=True)
                        polymarket_data['key_events'] = polymarket_data['key_events'][:10]  # 只保留前10个
                        
            except Exception as e:
                print(f"Polymarket GraphQL API请求失败: {e}")
                # 如果GraphQL失败，尝试使用REST API
                try:
                    # 尝试获取市场数据（使用REST端点，如果可用）
                    rest_url = f"{base_url}/markets"
                    rest_response = requests.get(rest_url, timeout=10)
                    if rest_response.status_code == 200:
                        # 处理REST API响应
                        # 这里需要根据实际的REST API格式调整
                        pass
                except Exception as rest_error:
                    print(f"Polymarket REST API请求也失败: {rest_error}")
            
            # 计算综合市场情绪（基于预测市场的概率）
            # 如果无法获取实时数据，使用默认值
            if len(polymarket_data['key_events']) > 0:
                # 基于关键事件的流动性加权平均
                total_liquidity = sum(event.get('liquidity', 0) for event in polymarket_data['key_events'])
                if total_liquidity > 0:
                    # 这里可以根据实际预测概率计算情绪
                    # 暂时使用一个基于事件数量的简单指标
                    polymarket_data['overall_sentiment'] = min(10, len(polymarket_data['key_events']) * 0.5)
            
        except Exception as e:
            print(f"获取Polymarket数据时出错: {e}")
    
    except Exception as e:
        print(f"Polymarket数据获取异常: {e}")

    return polymarket_data


def calculate_market_correlation(ticker, benchmark='SPY', period='6mo'):
    """
    计算个股与大盘的相关性

    用于检测风险聚集：高相关性意味着个股与大盘同涨同跌，
    在市场下跌时无法提供分散化保护。

    参数:
        ticker: 股票代码
        benchmark: 基准指数（默认SPY）
        period: 计算周期（默认6个月）

    返回:
        dict: {
            'current_correlation': 当前相关性,
            'avg_correlation': 平均相关性,
            'correlation_trend': 相关性趋势 ('rising'/'falling'/'stable'),
            'high_correlation_warning': 是否高度相关,
            'beta_estimate': 基于相关性估算的Beta
        }
    """
    try:
        normalized_ticker = normalize_ticker(ticker)

        # 下载股票和基准数据
        stock_data = yf.download(normalized_ticker, period=period, progress=False)
        benchmark_data = yf.download(benchmark, period=period, progress=False)

        if stock_data.empty or benchmark_data.empty:
            print(f"[相关性] {ticker}: 无法获取数据")
            return None

        # 获取收盘价
        stock_close = stock_data['Close']
        benchmark_close = benchmark_data['Close']

        # 对齐日期
        combined = pd.concat([stock_close, benchmark_close], axis=1).dropna()
        combined.columns = ['stock', 'benchmark']

        if len(combined) < 30:
            print(f"[相关性] {ticker}: 数据点不足({len(combined)})")
            return None

        # 计算日收益率
        combined['stock_return'] = combined['stock'].pct_change()
        combined['benchmark_return'] = combined['benchmark'].pct_change()
        combined = combined.dropna()

        # 计算整体相关性
        overall_corr = combined['stock_return'].corr(combined['benchmark_return'])

        # 计算60日滚动相关性
        rolling_corr = combined['stock_return'].rolling(60).corr(combined['benchmark_return'])
        rolling_corr = rolling_corr.dropna()

        if len(rolling_corr) < 10:
            current_corr = overall_corr
            avg_corr = overall_corr
            trend = 'stable'
        else:
            current_corr = rolling_corr.iloc[-1]
            avg_corr = rolling_corr.mean()

            # 判断趋势（最近30天 vs 之前30天）
            recent_corr = rolling_corr.iloc[-30:].mean() if len(rolling_corr) >= 30 else current_corr
            older_corr = rolling_corr.iloc[-60:-30].mean() if len(rolling_corr) >= 60 else avg_corr

            if recent_corr > older_corr + 0.1:
                trend = 'rising'
            elif recent_corr < older_corr - 0.1:
                trend = 'falling'
            else:
                trend = 'stable'

        # 计算Beta（股票收益率对大盘收益率的敏感度）
        if combined['benchmark_return'].std() > 0:
            cov = combined['stock_return'].cov(combined['benchmark_return'])
            var = combined['benchmark_return'].var()
            beta_estimate = cov / var if var > 0 else 1.0
        else:
            beta_estimate = 1.0

        # 高相关性警告阈值
        high_corr_threshold = 0.85

        result = {
            'current_correlation': round(float(current_corr), 3),
            'avg_correlation': round(float(avg_corr), 3),
            'correlation_trend': trend,
            'high_correlation_warning': current_corr > high_corr_threshold,
            'beta_estimate': round(float(beta_estimate), 2),
            'benchmark': benchmark,
            'period': period
        }

        print(f"[相关性] {ticker}: 当前相关性={current_corr:.3f}, 平均={avg_corr:.3f}, Beta={beta_estimate:.2f}, 趋势={trend}")

        return result

    except Exception as e:
        print(f"[相关性] {ticker}: 计算失败 - {e}")
        return None


def get_options_market_data(ticker):
    """
    获取期权市场相关数据
    包括VIX、期权持仓量、Put/Call比率等
    用于评估Vanna crush和负Gamma风险
    """
    options_data = {
        'vix': None,
        'vix_change': None,
        'put_call_ratio': None,
        'options_volume': None,
        'has_options': False  # 布尔值，JSON可以序列化
    }
    
    try:
        # 1. 获取VIX（恐慌指数）- 这是最重要的市场波动率指标
        try:
            vix_ticker = yf.Ticker('^VIX')
            vix_hist = vix_ticker.history(period='5d', timeout=10)
            if not vix_hist.empty and len(vix_hist) >= 2:
                vix_current = float(vix_hist['Close'].iloc[-1])
                vix_prev = float(vix_hist['Close'].iloc[-2])
                vix_change = ((vix_current - vix_prev) / vix_prev) * 100
                options_data['vix'] = float(vix_current)  # 确保是Python float
                options_data['vix_change'] = float(vix_change)  # 确保是Python float
        except Exception as e:
            print(f"获取VIX数据失败: {e}")
        
        # 2. 对于美股，尝试获取期权链数据
        # 判断是否为美股（不包含.HK, .SS, .SZ等后缀）
        normalized_ticker = normalize_ticker(ticker)
        is_us_stock = '.' not in normalized_ticker or normalized_ticker.endswith(('.US', ''))
        
        if is_us_stock:
            try:
                stock = yf.Ticker(normalized_ticker)
                # 获取最近的到期日期
                try:
                    expirations = stock.options
                    if expirations and len(expirations) > 0:
                        # 获取最近到期的期权链
                        nearest_exp = expirations[0]
                        opt_chain = stock.option_chain(nearest_exp)
                        
                        calls = opt_chain.calls
                        puts = opt_chain.puts
                        
                        # 计算Put/Call比率（持仓量）
                        if not calls.empty and not puts.empty:
                            put_volume = float(puts['openInterest'].sum() if 'openInterest' in puts.columns else puts['volume'].sum())
                            call_volume = float(calls['openInterest'].sum() if 'openInterest' in calls.columns else calls['volume'].sum())
                            
                            if call_volume > 0:
                                put_call_ratio = float(put_volume / call_volume)
                                options_data['put_call_ratio'] = put_call_ratio
                                options_data['options_volume'] = float(put_volume + call_volume)
                                options_data['has_options'] = True  # 布尔值，JSON可以序列化
                except Exception as e:
                    print(f"获取期权链数据失败: {e}")
            except Exception as e:
                print(f"期权数据获取异常: {e}")
    except Exception as e:
        print(f"获取期权市场数据时出错: {e}")
    
    return options_data


def calculate_atr(hist_data, period=14):
    """
    计算平均真实波幅（Average True Range, ATR）
    
    参数:
        hist_data: DataFrame，包含High, Low, Close列
        period: 计算ATR的周期（通常为14天）
    
    返回:
        ATR值（标量），如果数据不足则返回None
    """
    try:
        if hist_data.empty or len(hist_data) < period + 1:
            return None
        
        # 确保有High, Low, Close列
        if not all(col in hist_data.columns for col in ['High', 'Low', 'Close']):
            return None
        
        # 计算True Range的三个组成部分
        high_low = hist_data['High'] - hist_data['Low']
        high_close_prev = abs(hist_data['High'] - hist_data['Close'].shift(1))
        low_close_prev = abs(hist_data['Low'] - hist_data['Close'].shift(1))
        
        # True Range = max(high-low, high-close_prev, low-close_prev)
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # ATR = True Range的移动平均
        atr = true_range.rolling(window=period).mean()
        
        # 返回最新的ATR值
        if not atr.empty and not pd.isna(atr.iloc[-1]):
            return float(atr.iloc[-1])
        else:
            return None
    except Exception as e:
        print(f"计算ATR时出错: {e}")
        return None


def calculate_dynamic_peg_threshold(treasury_10y, base_peg_threshold=1.0):
    """
    根据10年美债收益率动态调整PEG阈值
    
    逻辑:
    - 美债收益率高 -> 资金成本高 -> 对成长股要求更严格 -> PEG阈值降低
    - 美债收益率低 -> 资金成本低 -> 对成长股容忍度提高 -> PEG阈值提高
    
    参数:
        treasury_10y: 当前10年期美债收益率（百分比，如4.5表示4.5%），如果为None则返回基础阈值
        base_peg_threshold: 基准PEG阈值（通常为1.0）
    
    返回:
        调整后的PEG阈值
    """
    if treasury_10y is None:
        return base_peg_threshold
    
    # 基准利率假设为3.0%（历史平均）
    base_rate = 3.0
    
    # 计算利率偏离度
    rate_deviation = treasury_10y - base_rate
    
    # 调整系数：每1%的利率偏离，PEG阈值调整0.15
    # 利率上升1% -> PEG阈值降低0.15（更严格）
    # 利率下降1% -> PEG阈值提高0.15（更宽松）
    adjustment_factor = 1.0 - (rate_deviation * 0.15)
    
    # 限制调整范围：PEG阈值在0.5-2.0之间
    dynamic_peg_threshold = max(0.5, min(2.0, base_peg_threshold * adjustment_factor))
    
    return dynamic_peg_threshold


def calculate_atr_stop_loss(buy_price, hist_data, atr_period=None, atr_multiplier=None, min_stop_loss_pct=None, beta=None, vix=None):
    """
    基于ATR计算动态止损价格

    参数:
        buy_price: 买入时的价格
        hist_data: DataFrame，包含High, Low, Close列
        atr_period: 计算ATR的周期（默认使用配置值）
        atr_multiplier: ATR的倍数（默认使用配置值）
        min_stop_loss_pct: 最小止损幅度（默认使用配置值）
        beta: 股票的Beta值（可选，如果提供则用于调整ATR倍数）
        vix: 当前VIX值（可选，如果提供则用于动态调整ATR倍数）

    返回:
        dict: 包含止损价格和调整详情
            - stop_loss_price: 止损价格
            - atr_multiplier: 最终使用的ATR倍数
            - adjustments: 调整说明列表
    """
    # 使用配置默认值
    if atr_period is None:
        atr_period = ATR_PERIOD
    if atr_multiplier is None:
        atr_multiplier = ATR_MULTIPLIER_BASE
    if min_stop_loss_pct is None:
        min_stop_loss_pct = FIXED_STOP_LOSS_PCT

    adjustments = []
    original_multiplier = atr_multiplier

    # ===== 新增: VIX动态调整 =====
    # VIX基准为20，高于20时需要更宽的止损空间
    # VIX每上升10点，ATR倍数增加0.3
    if vix is not None:
        if vix > 20:
            vix_adjustment = ((vix - 20) / 10) * 0.3
            vix_adjustment = min(vix_adjustment, 1.0)  # 最多增加1.0
            atr_multiplier = atr_multiplier + vix_adjustment
            adjustments.append(f"VIX调整: +{vix_adjustment:.2f} (VIX={vix:.1f})")
        elif vix < 15:
            # VIX很低时可以适当收紧止损
            vix_adjustment = -0.2
            atr_multiplier = atr_multiplier + vix_adjustment
            adjustments.append(f"低VIX调整: {vix_adjustment:.2f} (VIX={vix:.1f})")

    # 根据Beta调整ATR倍数（如果提供）
    if beta is not None:
        beta_adjustment = 0
        if beta > BETA_HIGH_THRESHOLD:
            # 高Beta股票，使用更大的倍数（更宽止损）
            beta_adjustment = atr_multiplier * (BETA_HIGH_MULTIPLIER - 1)
            atr_multiplier = atr_multiplier * BETA_HIGH_MULTIPLIER
            adjustments.append(f"高Beta调整: +{beta_adjustment:.2f} (Beta={beta:.2f})")
        elif beta > BETA_MID_HIGH_THRESHOLD:
            beta_adjustment = atr_multiplier * (BETA_MID_HIGH_MULTIPLIER - 1)
            atr_multiplier = atr_multiplier * BETA_MID_HIGH_MULTIPLIER
            adjustments.append(f"中高Beta调整: +{beta_adjustment:.2f} (Beta={beta:.2f})")
        elif beta < BETA_LOW_THRESHOLD:
            # 低Beta股票，使用更小的倍数（更窄止损）
            beta_adjustment = atr_multiplier * (BETA_LOW_MULTIPLIER - 1)
            atr_multiplier = atr_multiplier * BETA_LOW_MULTIPLIER
            adjustments.append(f"低Beta调整: {beta_adjustment:.2f} (Beta={beta:.2f})")
        elif beta < BETA_MID_LOW_THRESHOLD:
            beta_adjustment = atr_multiplier * (BETA_MID_LOW_MULTIPLIER - 1)
            atr_multiplier = atr_multiplier * BETA_MID_LOW_MULTIPLIER
            adjustments.append(f"中低Beta调整: {beta_adjustment:.2f} (Beta={beta:.2f})")

    # 限制倍数范围
    atr_multiplier = max(ATR_MULTIPLIER_MIN, min(ATR_MULTIPLIER_MAX, atr_multiplier))

    if atr_multiplier != original_multiplier:
        print(f"[ATR止损] ATR倍数从 {original_multiplier:.2f} 调整为 {atr_multiplier:.2f}, 调整: {', '.join(adjustments)}")

    # 计算ATR
    atr = calculate_atr(hist_data, atr_period)

    if atr is None or atr <= 0:
        # 如果无法计算ATR，使用最小止损幅度
        stop_loss_price = buy_price * (1 - min_stop_loss_pct)
    else:
        # 基于ATR计算止损价格
        atr_stop_loss_price = buy_price - (atr * atr_multiplier)

        # 硬止损价格（最小止损幅度）
        hard_stop_loss_price = buy_price * (1 - min_stop_loss_pct)

        # 取两者中更保守的（止损价格更低）
        stop_loss_price = min(atr_stop_loss_price, hard_stop_loss_price)

    # 返回详细结果（向后兼容：直接返回float时保持兼容）
    return {
        'stop_loss_price': stop_loss_price,
        'atr_multiplier': atr_multiplier,
        'adjustments': adjustments,
        'vix': vix,
        'beta': beta
    }


def calculate_market_sentiment(data):
    """
    计算市场情绪评分 (M维度)
    返回0-10分，分数越高表示市场情绪越乐观
    现在包含期权市场情绪指标（VIX、Put/Call比率等）和宏观经济指标
    对于A股/港股，还会包含中国市场特有的情绪指标（政策、资金流等）
    """
    sentiment_score = 5.0  # 基准分，中性
    
    # 判断市场类型
    symbol = data.get('symbol', '')
    is_cn_market = symbol.endswith('.SS') or symbol.endswith('.SZ')
    is_hk_market = symbol.endswith('.HK')
    
    # 获取中国市场特有情绪数据（如果是A股或港股）
    china_sentiment_data = {}
    china_policy_data = {}
    china_sentiment_adjustment = 0.0
    china_sentiment_adjustments = []
    
    if is_hk_market:
        try:
            from china_sentiment import (
                get_china_stock_sentiment, 
                get_china_macro_policy_signals,
                calculate_china_sentiment_score
            )
            
            market_type = 'CN' if is_cn_market else 'HK'
            china_sentiment_data = get_china_stock_sentiment(symbol, market=market_type)
            china_policy_data = get_china_macro_policy_signals()
            
            # 计算中国市场特有的情绪分数
            china_score, adjustments = calculate_china_sentiment_score(china_sentiment_data, china_policy_data)
            china_sentiment_adjustment = china_score - 5.0  # 相对于基准分的调整值
            china_sentiment_adjustments = adjustments
            
            # 存储到data中供AI分析使用
            data['china_sentiment'] = china_sentiment_data
            data['china_policy'] = china_policy_data
            data['china_sentiment_score'] = china_score
            data['china_sentiment_adjustments'] = adjustments
            
        except ImportError:
            print("警告: china_sentiment模块未找到，中国市场情绪数据将不可用（需要安装akshare: pip install akshare）")
        except Exception as e:
            print(f"获取中国市场情绪数据失败: {e}")
    
    # 获取期权市场数据
    options_data = get_options_market_data(data.get('original_symbol', data.get('symbol', '')))
    
    # 获取宏观经济数据
    macro_data = get_macro_market_data()
    
    # 获取Polymarket预测市场数据
    polymarket_data = get_polymarket_data()
    macro_data['polymarket'] = polymarket_data
    
    # 计算地缘政治风险指数（需要期权数据）
    if options_data:
        macro_data['geopolitical_risk'] = calculate_geopolitical_risk(macro_data, options_data)
    
    # 生成市场预警信息
    warnings = get_market_warnings(macro_data, options_data, data)
    data['market_warnings'] = warnings
    
    # 1. PE估值情绪 (权重30%，降低权重为期权指标让路)
    if data['pe'] and data['pe'] > 0:
        if data['pe'] < 10:
            pe_sentiment = 3.0  # 估值偏低，情绪悲观
        elif data['pe'] < 15:
            pe_sentiment = 4.0  # 估值合理偏低
        elif data['pe'] < 25:
            pe_sentiment = 5.0  # 估值合理
        elif data['pe'] < 40:
            pe_sentiment = 7.0  # 估值偏高，情绪乐观
        elif data['pe'] < 60:
            pe_sentiment = 8.5  # 估值很高，情绪很乐观
        else:
            pe_sentiment = 9.5  # 估值极高，情绪极度乐观（可能泡沫）
        sentiment_score = pe_sentiment * 0.3
    else:
        # 如果没有PE数据，使用中性分
        sentiment_score = 5.0 * 0.3
    
    # 2. PEG情绪调整 (权重15%) - 使用动态阈值
    if data['peg'] and data['peg'] > 0:
        # 获取10年美债收益率，用于动态调整PEG阈值
        treasury_10y = macro_data.get('treasury_10y')
        dynamic_peg_threshold = calculate_dynamic_peg_threshold(treasury_10y, base_peg_threshold=1.0)
        
        # 使用动态阈值计算PEG情绪分数
        if data['peg'] < dynamic_peg_threshold * 0.7:
            peg_sentiment = 8.0  # PEG很低，增长预期高，情绪乐观
        elif data['peg'] < dynamic_peg_threshold:
            peg_sentiment = 6.0  # PEG合理，增长匹配估值
        elif data['peg'] < dynamic_peg_threshold * 1.3:
            peg_sentiment = 5.0  # PEG略高，中性
        else:
            peg_sentiment = 3.0  # PEG过高，增长不匹配，情绪悲观
        
        # 存储动态PEG阈值供后续使用
        data['dynamic_peg_threshold'] = dynamic_peg_threshold
        
        sentiment_score += peg_sentiment * 0.15
    else:
        # 如果没有PEG数据，使用中性分
        sentiment_score += 5.0 * 0.15
    
    # 3. 价格位置情绪 (权重25%)
    if data.get('week52_high') and data.get('week52_low') and data['week52_high'] > data['week52_low']:
        price_position = (data['price'] - data['week52_low']) / (data['week52_high'] - data['week52_low'])
        # 确保price_position在合理范围内
        price_position = max(0, min(1, price_position))
        if price_position < 0.2:
            position_sentiment = 2.0  # 接近低点，情绪悲观
        elif price_position < 0.4:
            position_sentiment = 4.0  # 偏低位置
        elif price_position < 0.6:
            position_sentiment = 5.0  # 中间位置，中性
        elif price_position < 0.8:
            position_sentiment = 7.0  # 偏高位置，情绪乐观
        else:
            position_sentiment = 8.5  # 接近高点，情绪很乐观
        sentiment_score += position_sentiment * 0.25
    else:
        # 如果52周高低价相同，使用中性情绪
        sentiment_score += 5.0 * 0.25
    
    # 4. 技术面情绪 (权重10%)
    if data['price'] > data['ma50'] and data['ma50'] > data['ma200']:
        tech_sentiment = 7.0  # 多头排列，情绪偏乐观
    elif data['price'] < data['ma200']:
        tech_sentiment = 3.0  # 跌破长期均线，情绪偏悲观
    else:
        tech_sentiment = 5.0  # 震荡，中性
    sentiment_score += tech_sentiment * 0.1
    
    # 5. 期权市场情绪 (权重20%) - 新增！
    # 5.1 VIX恐慌指数 (权重12%)
    if options_data['vix'] is not None:
        vix = options_data['vix']
        vix_change = options_data.get('vix_change', 0)
        
        # VIX越高，市场恐慌情绪越高，情绪评分越低
        # VIX正常范围：10-20（低波动），20-30（中等波动），30+（高波动/恐慌）
        if vix < 15:
            vix_sentiment = 8.0  # 低波动，市场平静，情绪乐观
        elif vix < 20:
            vix_sentiment = 6.5  # 正常波动
        elif vix < 25:
            vix_sentiment = 5.0  # 中等偏高波动
        elif vix < 30:
            vix_sentiment = 3.5  # 高波动，情绪偏悲观
        elif vix < 40:
            vix_sentiment = 2.0  # 很高波动，恐慌情绪
        else:
            vix_sentiment = 1.0  # 极高波动，极度恐慌
        
        # VIX快速上升（>10%）表示恐慌加剧，进一步降低情绪
        if vix_change > 10:
            vix_sentiment = max(1.0, vix_sentiment - 1.5)  # 恐慌加剧
        elif vix_change > 5:
            vix_sentiment = max(1.0, vix_sentiment - 0.8)
        elif vix_change < -10:
            vix_sentiment = min(10.0, vix_sentiment + 1.0)  # 恐慌缓解
        
        sentiment_score += vix_sentiment * 0.12
    else:
        sentiment_score += 5.0 * 0.12
    
    # 5.2 Put/Call比率 (权重8%)
    # Put/Call比率高 -> 看跌情绪强 -> 市场情绪悲观
    if options_data['put_call_ratio'] is not None:
        pc_ratio = options_data['put_call_ratio']
        # 正常范围：0.7-1.0（中性），>1.0（看跌情绪强），<0.7（看涨情绪强）
        if pc_ratio < 0.7:
            pc_sentiment = 7.5  # 看涨情绪强
        elif pc_ratio < 0.9:
            pc_sentiment = 6.0  # 略偏看涨
        elif pc_ratio < 1.1:
            pc_sentiment = 5.0  # 中性
        elif pc_ratio < 1.3:
            pc_sentiment = 4.0  # 略偏看跌
        elif pc_ratio < 1.5:
            pc_sentiment = 3.0  # 看跌情绪较强
        else:
            pc_sentiment = 2.0  # 极度看跌（可能负Gamma风险）
        
        sentiment_score += pc_sentiment * 0.08
    else:
        sentiment_score += 5.0 * 0.08
    
    # 6. 宏观经济情绪调整 (权重10%) - 新增！
    # 6.1 美债收益率 (权重4%) - 收益率上升通常意味着流动性收紧，对股市不利
    if macro_data['treasury_10y'] is not None:
        treasury = macro_data['treasury_10y']
        treasury_change = macro_data.get('treasury_10y_change', 0)
        
        # 收益率在3-4%为正常，>4.5%表示紧缩，<2.5%表示宽松
        if treasury < 2.5:
            treasury_sentiment = 7.0  # 宽松环境，利好股市
        elif treasury < 3.5:
            treasury_sentiment = 6.0  # 正常偏低
        elif treasury < 4.5:
            treasury_sentiment = 5.0  # 正常
        elif treasury < 5.0:
            treasury_sentiment = 4.0  # 偏高，流动性收紧
        else:
            treasury_sentiment = 2.5  # 很高，严重收紧
        
        # 快速上升（>0.2%）进一步降低情绪
        if treasury_change > 0.2:
            treasury_sentiment = max(1.0, treasury_sentiment - 1.0)
        elif treasury_change < -0.2:
            treasury_sentiment = min(10.0, treasury_sentiment + 0.5)
        
        sentiment_score += treasury_sentiment * 0.04
    else:
        sentiment_score += 5.0 * 0.04
    
    # 6.2 美元指数 (权重3%) - 美元走强通常对美股不利（资金流出）
    if macro_data['dxy'] is not None:
        dxy = macro_data['dxy']
        dxy_change = macro_data.get('dxy_change', 0)
        
        # DXY正常范围：95-105，>105表示强势美元，<95表示弱势
        if dxy < 95:
            dxy_sentiment = 6.5  # 弱势美元，利好
        elif dxy < 105:
            dxy_sentiment = 5.0  # 正常
        else:
            dxy_sentiment = 3.5  # 强势美元，不利
        
        # 快速上升（>1%）进一步降低情绪
        if dxy_change > 1:
            dxy_sentiment = max(1.0, dxy_sentiment - 0.8)
        
        sentiment_score += dxy_sentiment * 0.03
    else:
        sentiment_score += 5.0 * 0.03
    
    # 6.3 黄金价格 (权重2%) - 避险情绪指标
    if macro_data['gold'] is not None:
        gold_change = macro_data.get('gold_change', 0)
        
        # 黄金上涨通常表示避险情绪上升，对股市不利
        if gold_change > 2:
            gold_sentiment = 3.0  # 避险情绪强烈
        elif gold_change > 0.5:
            gold_sentiment = 4.5  # 略有避险
        elif gold_change < -2:
            gold_sentiment = 7.0  # 风险偏好上升
        else:
            gold_sentiment = 5.0  # 中性
        
        sentiment_score += gold_sentiment * 0.02
    else:
        sentiment_score += 5.0 * 0.02
    
    # 6.4 原油价格 (权重1%) - 通胀和增长预期
    if macro_data['oil'] is not None:
        oil_change = macro_data.get('oil_change', 0)
        
        # 原油大幅上涨可能引发通胀担忧，但适度上涨表示需求增长
        if oil_change > 5:
            oil_sentiment = 4.0  # 通胀担忧
        elif oil_change < -5:
            oil_sentiment = 4.5  # 需求疲软
        else:
            oil_sentiment = 5.0  # 中性
        
        sentiment_score += oil_sentiment * 0.01
    else:
        sentiment_score += 5.0 * 0.01
    
    # 7. Polymarket预测市场情绪 (权重3%) - 反映市场对重大事件的预期
    if polymarket_data and polymarket_data.get('overall_sentiment') is not None:
        polymarket_sentiment = polymarket_data['overall_sentiment']
        sentiment_score += polymarket_sentiment * 0.03
    else:
        sentiment_score += 5.0 * 0.03
    
    # 7.1 基于Polymarket关键事件调整情绪
    if polymarket_data and polymarket_data.get('key_events'):
        key_events = polymarket_data['key_events']
        # 检查是否有负面事件（如经济衰退、市场崩盘等）
        negative_keywords = ['recession', 'crash', 'crisis', 'war', 'conflict', 'sanction']
        positive_keywords = ['rally', 'growth', 'recovery', 'peace', 'deal']
        
        negative_count = 0
        positive_count = 0
        
        for event in key_events:
            question = event.get('question', '').lower()
            if any(keyword in question for keyword in negative_keywords):
                negative_count += 1
            elif any(keyword in question for keyword in positive_keywords):
                positive_count += 1
        
        # 负面事件多于正面事件时，降低情绪
        if negative_count > positive_count:
            sentiment_score -= (negative_count - positive_count) * 0.2
        elif positive_count > negative_count:
            sentiment_score += (positive_count - negative_count) * 0.1
    
    # 7. 期权到期日对市场情绪的影响 (权重2%) - 市场级别风险
    # 期权到期日会导致市场波动增加，降低市场情绪
    if macro_data.get('options_expirations'):
        expiration_impact = 0
        for exp in macro_data['options_expirations']:
            days_until = exp['days_until']
            is_quadruple = exp.get('is_quadruple_witching', False)
            
            # 距离到期日越近，对市场情绪的影响越大
            # 期权到期日会导致做市商调整对冲，增加市场波动，降低市场情绪
            if days_until <= 1:
                # 当天或明天到期，市场波动风险最高
                impact = -2.0 if is_quadruple else -1.5  # 四重到期日影响更大
            elif days_until <= 3:
                impact = -1.5 if is_quadruple else -1.0
            elif days_until <= 7:
                impact = -1.0 if is_quadruple else -0.5
            elif days_until <= 14:
                impact = -0.5 if is_quadruple else -0.3
            else:
                impact = 0
            
            expiration_impact += impact
        
        # 限制最大影响（避免过度调整）
        expiration_impact = max(-2.0, min(0, expiration_impact))
        sentiment_score += expiration_impact * 0.02
    else:
        sentiment_score += 0.0 * 0.02
    
    # 将期权和宏观经济数据存储到data中，供前端和AI分析使用
    data['options_data'] = options_data
    data['macro_data'] = macro_data

    # 计算与大盘的相关性（用于风险聚集检测）
    try:
        correlation_result = calculate_market_correlation(symbol)
        if correlation_result:
            data['market_correlation'] = correlation_result

            # 如果高度相关且是高Beta，增加风险警示
            if correlation_result.get('high_correlation_warning'):
                beta = correlation_result.get('beta_estimate', 1.0)
                if beta > 1.2:
                    # 高相关 + 高Beta = 市场下跌时损失更大
                    sentiment_score -= 0.3
                    print(f"[情绪] {symbol}: 高相关性+高Beta警告，情绪下调0.3")
    except Exception as e:
        print(f"[情绪] {symbol}: 相关性计算失败 - {e}")

    # 对于A股/港股，应用中国市场特有的情绪调整
    # 中国市场：政策>一切，权重更高（40%）
    if is_cn_market or is_hk_market:
        if china_sentiment_adjustment != 0:
            # 中国市场情绪调整权重：40%（政策权重最高）
            # 混合计算：60%使用传统指标，40%使用中国市场特有指标
            sentiment_score = sentiment_score * 0.6 + (5.0 + china_sentiment_adjustment) * 0.4
            data['china_sentiment_weight'] = 0.4
            data['china_sentiment_used'] = True
        else:
            data['china_sentiment_weight'] = 0
            data['china_sentiment_used'] = False
    else:
        data['china_sentiment_weight'] = 0
        data['china_sentiment_used'] = False
    
    # 确保分数在0-10范围内
    sentiment_score = max(0, min(10, sentiment_score))
    
    return round(sentiment_score, 1)


def is_etf_or_fund(data):
    """
    判断是否为ETF或基金
    返回：是否为ETF/基金，类型（ETF/Fund/Stock）
    """
    sector = data.get('sector', '').lower()
    industry = data.get('industry', '').lower()
    name = data.get('name', '').lower()
    symbol = data.get('symbol', '').lower()
    
    # 关键词检测（扩展关键词列表）
    etf_keywords = [
        'etf', 'exchange traded fund', 'index fund', 'tracker',
        'proshares', 'ultrapro', 'ultra', 'invesco', 'ishares',
        'vanguard', 'spdr', 'ark', 'leveraged', 'inverse',
        '3x', '2x', 'qqq', 'spy', 'dow', 'nasdaq'
    ]
    fund_keywords = ['mutual fund', 'fund', 'trust', 'reit', 'reits', 'closed-end']
    
    # 检查名称和行业
    name_sector_industry = f"{name} {sector} {industry} {symbol}"
    
    # 检查ETF关键词（优先级更高）
    if any(keyword in name_sector_industry for keyword in etf_keywords):
        return True, 'ETF'
    elif any(keyword in name_sector_industry for keyword in fund_keywords):
        # REIT是特殊的，也算基金类
        if 'reit' in name_sector_industry:
            return True, 'REIT'
        return True, 'Fund'
    
    # 检查symbol后缀（某些ETF有特定后缀）
    if symbol.endswith(('.x', '.xshg', '.xsz')):  # 某些ETF后缀
        return True, 'ETF'
    
    # 检查行业分类（某些行业通常是ETF）
    if sector in ['unknown', ''] and industry in ['unknown', '']:
        # 如果行业信息缺失，且名称中包含常见ETF特征，可能是ETF
        if any(keyword in name for keyword in ['ultra', 'pro', 'leveraged', 'inverse']):
            return True, 'ETF'
    
    return False, 'Stock'


def classify_company(data):
    """
    对公司进行分类
    返回：公司类别、行业特征、成长阶段等
    """
    # 首先检查是否为ETF或基金
    is_fund, fund_type = is_etf_or_fund(data)
    if is_fund:
        return {
            'is_etf_or_fund': True,
            'fund_type': fund_type,
            'industry_category': 'fund',
            'growth_stage': 'fund',  # 基金不适用成长阶段
            'market_cap_category': 'fund',
            'sector': data.get('sector', 'Fund'),
            'industry': data.get('industry', 'Fund')
        }
    
    sector = data.get('sector', 'Unknown').lower()
    industry = data.get('industry', 'Unknown').lower()
    growth = data.get('growth', 0)
    pe = data.get('pe', 0)
    market_cap = data.get('market_cap', 0)  # 市值（美元）
    
    # 1. 按行业分类
    industry_category = 'general'
    if any(keyword in sector or keyword in industry for keyword in ['technology', 'software', 'internet', 'semiconductor', 'tech']):
        industry_category = 'technology'
    elif any(keyword in sector or keyword in industry for keyword in ['financial', 'bank', 'insurance', 'finance']):
        industry_category = 'financial'
    elif any(keyword in sector or keyword in industry for keyword in ['healthcare', 'pharmaceutical', 'biotech', 'medical']):
        industry_category = 'healthcare'
    elif any(keyword in sector or keyword in industry for keyword in ['energy', 'oil', 'gas', 'petroleum']):
        industry_category = 'energy'
    elif any(keyword in sector or keyword in industry for keyword in ['consumer', 'retail', 'consumer goods']):
        industry_category = 'consumer'
    elif any(keyword in sector or keyword in industry for keyword in ['real estate', 'reit', 'property']):
        industry_category = 'real_estate'
    elif any(keyword in sector or keyword in industry for keyword in ['utility', 'utilities', 'electric']):
        industry_category = 'utility'
    
    # 2. 按成长阶段分类
    growth_stage = 'mature'
    if growth > 0.2:  # 营收增长>20%
        growth_stage = 'high_growth'
    elif growth > 0.1:  # 营收增长>10%
        growth_stage = 'growth'
    elif growth > 0:  # 正增长
        growth_stage = 'stable'
    else:  # 负增长或零增长
        growth_stage = 'declining'
    
    # 3. 按市值分类
    market_cap_category = 'mid_cap'
    if market_cap > 0:
        if market_cap > 100e9:  # >1000亿美元
            market_cap_category = 'large_cap'
        elif market_cap > 10e9:  # >100亿美元
            market_cap_category = 'mid_cap'
        else:
            market_cap_category = 'small_cap'
    
    return {
        'is_etf_or_fund': False,
        'fund_type': None,
        'industry_category': industry_category,
        'growth_stage': growth_stage,
        'market_cap_category': market_cap_category,
        'sector': sector,
        'industry': industry
    }


def get_reasonable_pe_by_category(company_info, style):
    """
    根据公司类别和投资风格，确定合理的PE倍数
    """
    industry_category = company_info['industry_category']
    growth_stage = company_info['growth_stage']
    
    # 基础PE（根据行业）
    base_pe = {
        'technology': 25,
        'healthcare': 22,
        'financial': 12,
        'energy': 15,
        'consumer': 18,
        'real_estate': 15,
        'utility': 16,
        'general': 18
    }.get(industry_category, 18)
    
    # 根据成长阶段调整
    if growth_stage == 'high_growth':
        base_pe *= 1.3  # 高成长公司可以容忍更高PE
    elif growth_stage == 'growth':
        base_pe *= 1.15
    elif growth_stage == 'stable':
        base_pe *= 1.0
    elif growth_stage == 'declining':
        base_pe *= 0.7  # 衰退公司PE应该更低
    
    # 根据投资风格调整
    if style == 'value':
        base_pe *= 0.75  # 价值风格要求更低PE
    elif style == 'growth':
        base_pe *= 1.2  # 成长风格可以容忍更高PE
    elif style == 'quality':
        base_pe *= 1.0  # 质量风格保持基准
    elif style == 'momentum':
        base_pe *= 1.1  # 趋势风格略高
    
    return round(base_pe, 1)


def calculate_target_price(data, risk_result, style):
    """
    计算目标价格 - 成熟的多维度估值模型
    根据公司类别（行业、成长阶段、市值）采用不同的估值方法和权重
    """
    try:
        current_price = float(data.get('price', 0))
        if current_price <= 0:
            return 0.0
    except (ValueError, TypeError):
        return 0.0
    
    # 如果建议仓位为0%，风险极高，不建议买入
    if risk_result['suggested_position'] == 0:
        return round(current_price, 2)
    
    # 对公司进行分类
    company_info = classify_company(data)
    
    # 如果是ETF或基金，使用不同的估值方法
    if company_info.get('is_etf_or_fund'):
        # ETF/基金的估值主要基于技术面和跟踪误差
        # 使用52周区间和技术指标
        week52_high = data.get('week52_high', current_price)
        week52_low = data.get('week52_low', current_price)
        ma50 = data.get('ma50', current_price)
        ma200 = data.get('ma200', current_price)
        
        # ETF目标价：基于均线和52周区间
        if current_price > ma50 and ma50 > ma200:
            # 上升趋势
            target_price = min(week52_high, current_price * 1.1)
        else:
            # 下降或震荡趋势
            target_price = (week52_high + week52_low) / 2
        
        data['target_price_methods'] = ['ETF/基金估值（技术面）']
        return round(target_price, 2)
    
    # 获取合理PE（根据公司类别和投资风格）
    reasonable_pe = get_reasonable_pe_by_category(company_info, style)
    
    prices = []
    methods_used = []
    
    # 方法1: PE/PEG估值法（适用于有盈利的公司）
    # 如果PE为0或缺失，跳过此方法，使用其他方法
    pe = data.get('pe', 0)
    if pe and pe > 0:
        forward_pe = data.get('forward_pe', 0)
        
        if 0 and forward_pe and forward_pe > 0:
            # 使用预期PE计算
            pe_based_price = current_price * (reasonable_pe / forward_pe)
        else:
            # 使用当前PE计算
            if pe > reasonable_pe * 1.5:
                # PE过高，目标价格下调
                pe_based_price = current_price * (reasonable_pe / pe)
            elif pe < reasonable_pe * 0.7:
                # PE偏低，有上涨空间
                pe_based_price = current_price * (reasonable_pe / pe) * 0.9
            else:
                # PE合理，给予适度溢价
                pe_based_price = current_price * (reasonable_pe / pe) * 0.95
        
        prices.append(pe_based_price)
        methods_used.append('PE估值')
    
    # 方法2: PEG估值法（适用于成长股）
    if data.get('peg') and data['peg'] > 0 and data.get('growth') and data['growth'] > 0:
        peg = data['peg']
        growth = data['growth']
        
        # 获取宏观经济数据以计算动态PEG阈值
        macro_data = get_macro_market_data()
        dynamic_peg_threshold = get_dynamic_peg_threshold(macro_data)
        
        # 合理PEG（基于动态阈值调整）
        reasonable_peg = dynamic_peg_threshold
        if company_info['growth_stage'] == 'high_growth':
            reasonable_peg = dynamic_peg_threshold * 1.2  # 高成长可以容忍更高PEG
        elif company_info['growth_stage'] == 'declining':
            reasonable_peg = dynamic_peg_threshold * 0.8  # 衰退公司PEG应该更低
        
        if peg < reasonable_peg:
            # PEG偏低，有上涨空间
            peg_multiplier = reasonable_peg / peg
            peg_based_price = current_price * min(peg_multiplier, 1.5)  # 限制最大涨幅
            prices.append(peg_based_price)
            methods_used.append('PEG估值')
    
    # 方法3: 增长率折现法（适用于成长股）
    if data.get('growth') and data['growth'] > 0:
        growth = data['growth']
        margin = data.get('margin', 0)
        
        # 根据成长阶段给予不同的增长溢价
        if company_info['growth_stage'] == 'high_growth':
            # 高成长公司：给予未来1-2年的增长预期
            growth_multiplier = 1 + growth * GROWTH_DISCOUNT_FACTOR
        elif company_info['growth_stage'] == 'growth':
            growth_multiplier = 1 + growth * (GROWTH_DISCOUNT_FACTOR * 0.67)  # 40% = 60% * 0.67
        elif company_info['growth_stage'] == 'stable':
            growth_multiplier = 1 + growth * 0.2  # 给予20%的增长溢价
        else:
            growth_multiplier = 1.0  # 衰退公司不给增长溢价
        
        # 如果利润率较高，可以给予更高估值
        if margin > 0.15:
            growth_multiplier *= 1.1
        
        growth_based_price = current_price * growth_multiplier
        prices.append(growth_based_price)
        methods_used.append('增长率折现')
    
    # 方法4: DCF估值法（适用于有稳定现金流的公司）
    try:
        free_cash_flow = data.get('free_cash_flow', 0)
        shares_outstanding = data.get('shares_outstanding', 0)
        growth = data.get('growth', 0.05)

        if free_cash_flow and free_cash_flow > 0 and shares_outstanding and shares_outstanding > 0:
            # 简化DCF模型
            # 折现率 = 无风险利率 + 风险溢价
            risk_free_rate = 0.04  # 当前美债收益率约4%
            risk_score = risk_result.get('score', 5)
            risk_premium = 0.03 + (risk_score / 100)  # 基于风险评分的溢价 (3%-13%)
            discount_rate = risk_free_rate + risk_premium

            # 确保增长率合理
            growth_rate = max(0, min(growth, 0.30))  # 限制在0-30%

            # 5年预测现金流
            fcf_projections = []
            current_fcf = free_cash_flow
            for year in range(1, 6):
                # 增长率逐年递减
                year_growth = growth_rate * (0.9 ** (year - 1))
                projected_fcf = current_fcf * (1 + year_growth)
                discounted = projected_fcf / ((1 + discount_rate) ** year)
                fcf_projections.append(discounted)
                current_fcf = projected_fcf

            # 永续价值 (Gordon Growth Model)
            terminal_growth = min(growth_rate * 0.3, 0.025)  # 永续增长率不超过2.5%
            if discount_rate > terminal_growth:
                terminal_value = fcf_projections[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
                terminal_pv = terminal_value / ((1 + discount_rate) ** 5)
            else:
                terminal_pv = fcf_projections[-1] * 10  # 保守估计

            # 企业价值
            enterprise_value = sum(fcf_projections) + terminal_pv

            # 股权价值 (简化：假设无净债务)
            equity_value = enterprise_value

            # 每股目标价
            dcf_based_price = equity_value / shares_outstanding

            # 限制DCF目标价在合理范围内（当前价格的50%-300%）
            dcf_based_price = max(current_price * 0.5, min(dcf_based_price, current_price * 3.0))

            prices.append(dcf_based_price)
            methods_used.append('DCF估值')
            print(f"[目标价] DCF估值: FCF={free_cash_flow:,.0f}, 折现率={discount_rate:.2%}, 目标价={dcf_based_price:.2f}")
    except Exception as e:
        print(f"计算DCF目标价格时出错: {e}")

    # 方法5: 技术面目标价（适用于所有公司，但权重较低）
    try:
        week52_high = float(data.get('week52_high') or current_price)
        week52_low = float(data.get('week52_low') or current_price)
        ma50 = float(data.get('ma50') or current_price)
        ma200 = float(data.get('ma200') or current_price)

        price_position = 0.5
        if week52_high and week52_low and week52_high > week52_low:
            price_position = (current_price - week52_low) / (week52_high - week52_low)
            price_position = max(0, min(1, price_position))

        # 根据价格位置和技术趋势确定目标价
        if price_position < 0.3:
            # 价格在低位
            if current_price > ma50 and ma50 > ma200:
                # 多头排列，目标价可以是52周高点
                tech_based_price = week52_high
            else:
                # 技术面一般，目标价保守（52周中位）
                tech_based_price = (week52_high + week52_low) / 2
        elif price_position < 0.7:
            # 价格在中位
            if current_price > ma50 and ma50 > ma200:
                tech_based_price = week52_high
            else:
                tech_based_price = current_price * 1.15
        else:
            # 价格在高位，目标价保守
            tech_based_price = current_price * 1.1

        prices.append(tech_based_price)
        methods_used.append('技术面分析')
    except (ValueError, TypeError, ZeroDivisionError) as e:
        print(f"计算技术面目标价格时出错: {e}")
    
    # 综合计算
    if not prices:
        # 如果都没有数据，使用保守估计
        target_price = current_price * 1.1
        methods_used = ['保守估计']
    else:
        # 根据公司类别和投资风格，给不同方法分配权重
        industry_category = company_info['industry_category']

        if industry_category in ['technology', 'healthcare']:
            # 科技和医疗：更重视增长率和PEG，DCF权重中等
            weights = {'PE估值': 0.20, 'PEG估值': 0.25, '增长率折现': 0.25, 'DCF估值': 0.20, '技术面分析': 0.10}
        elif industry_category == 'financial':
            # 金融：更重视PE，DCF对金融业适用性较低
            weights = {'PE估值': 0.45, 'PEG估值': 0.15, '增长率折现': 0.15, 'DCF估值': 0.10, '技术面分析': 0.15}
        elif industry_category in ['energy', 'utility']:
            # 能源和公用事业：更重视PE和DCF（现金流稳定）
            weights = {'PE估值': 0.30, 'PEG估值': 0.10, '增长率折现': 0.15, 'DCF估值': 0.30, '技术面分析': 0.15}
        elif industry_category in ['consumer', 'industrial']:
            # 消费和工业：DCF权重较高（现金流可预测）
            weights = {'PE估值': 0.25, 'PEG估值': 0.20, '增长率折现': 0.20, 'DCF估值': 0.25, '技术面分析': 0.10}
        else:
            # 其他行业：均衡权重
            weights = {'PE估值': 0.25, 'PEG估值': 0.20, '增长率折现': 0.20, 'DCF估值': 0.20, '技术面分析': 0.15}
        
        # 计算加权平均
        weighted_sum = 0
        total_weight = 0
        for i, price in enumerate(prices):
            method = methods_used[i] if i < len(methods_used) else '其他'
            weight = weights.get(method, 0.25)  # 默认权重
            weighted_sum += price * weight
            total_weight += weight
        
        if total_weight > 0:
            avg_price = weighted_sum / total_weight
        else:
            avg_price = sum(prices) / len(prices)
        
        # 根据风险评分调整
        risk_score = risk_result.get('score', 5)
        if risk_score >= 6:
            risk_adjustment = 0.85  # 高风险，目标价格下调15%
        elif risk_score >= 4:
            risk_adjustment = 0.95  # 中等风险，目标价格下调5%
        elif risk_score >= 2:
            risk_adjustment = 1.0   # 低风险，不调整
        else:
            risk_adjustment = 1.05  # 极低风险，可以稍微乐观
        
        target_price = avg_price * risk_adjustment
        
        # 根据投资风格进行最终调整
        if style == 'value':
            target_price *= 0.95  # 价值风格更保守
        elif style == 'growth':
            target_price *= 1.05  # 成长风格可以稍微乐观
        elif style == 'momentum':
            target_price *= 1.08  # 趋势风格可以更乐观
        
        # 确保目标价格在合理范围内
        # 最低不低于当前价格的80%，最高不超过当前价格的250%
        target_price = max(current_price * 0.8, min(target_price, current_price * 2.5))
        
        # 优化：如果计算出的目标价格远低于当前价格（说明当前价格被高估），
        # 我们需要调整逻辑，确保目标价格不会不合理地低于当前价格
        # 如果目标价格低于当前价格的95%，说明估值模型认为当前价格被高估
        # 在这种情况下，我们应该：
        # 1. 设置目标价格为当前价格的95-100%，作为"重新评估后的合理价格"
        # 2. 这样AI在生成报告时会知道当前价格已经达到或超过目标价格，应该考虑止盈
        if target_price < current_price * 0.95:
            # 当前价格可能被高估，但为了卖出建议的合理性，我们设置目标价格为当前价格的95%
            # 这表示"如果价格继续上涨，可以考虑在目标价格（当前价格的95%）附近止盈"
            # 但实际上，由于当前价格已经超过这个目标价格，AI会建议立即考虑止盈或减仓
            # 存储原始目标价格（用于说明估值情况）
            data['original_target_price'] = target_price
            # 设置新的目标价格为当前价格的95%，作为止盈参考点
            target_price = current_price * 0.95
    
    # 存储计算方法信息（用于前端显示）
    data['target_price_methods'] = methods_used
    data['target_price_reasonable_pe'] = reasonable_pe
    data['company_category'] = company_info
    
    return round(target_price, 2)


def analyze_risk_and_position(style, data):
    """
    基于胡猛模型和五大支柱进行硬逻辑计算
    """
    # 首先检查流动性（硬性门槛）
    is_liquid = data.get('is_liquid', True)
    liquidity_info = data.get('liquidity_check', {})
    
    if not is_liquid:
        # 流动性不足，直接返回高风险，建议仓位为0
        return {
            "score": 10,
            "level": "极高 (流动性不足，禁止交易)",
            "flags": [data.get('liquidity_warning', '流动性不足，日均成交额低于最低要求')],
            "suggested_position": 0.0,
            "liquidity_rejected": True
        }
    
    # 首先检查是否为ETF或基金
    is_fund, fund_type = is_etf_or_fund(data)
    if is_fund:
        # ETF和基金使用不同的风险评估逻辑
        risk_score = 0
        risk_flags = []
        
        # ETF/基金的风险主要来自：
        # 1. 价格位置（高位风险）
        price_position = 0.5
        if data.get('week52_high') and data.get('week52_low') and data['week52_high'] > data['week52_low']:
            price_position = (data['price'] - data['week52_low']) / (data['week52_high'] - data['week52_low'])
        
        if price_position > 0.8:
            risk_score += 2
            risk_flags.append(f"{fund_type}: 价格位于52周高位（{price_position*100:.1f}%），追高风险")
        elif price_position > 0.6:
            risk_score += 1
            risk_flags.append(f"{fund_type}: 价格偏高（{price_position*100:.1f}%）")
        
        # 2. 技术面（跌破长期均线）
        if data['price'] < data['ma200']:
            risk_score += 1.5
            risk_flags.append(f"{fund_type}: 价格跌破200日均线，长期趋势转弱")
        elif data['price'] < data['ma50']:
            risk_score += 0.5
        
        # 3. ETF/基金不适合用PE等指标评估，使用技术面为主
        # 仓位建议：ETF可以稍微放宽，但也要控制风险
        base_caps = {
            'value': 15,    # ETF价值风格可以稍微高一点
            'growth': 20,   # ETF成长风格
            'quality': 25,  # ETF质量风格
            'momentum': 8   # ETF趋势风格
        }
        max_cap = base_caps.get(style, 15)
        
        # 风险调整
        adjustment = 1.0
        if risk_score >= 4:
            adjustment = 0.0
        elif risk_score >= 3:
            adjustment = 0.5
        elif risk_score >= 2:
            adjustment = 0.7
        elif risk_score >= 1:
            adjustment = 0.85
        
        suggested_position = max_cap * adjustment
        
        risk_level = "低"
        if risk_score >= 4:
            risk_level = "极高 (建议观望)"
        elif risk_score >= 3:
            risk_level = "高"
        elif risk_score >= 2:
            risk_level = "中"
        
        return {
            "score": risk_score,
            "level": risk_level,
            "flags": risk_flags,
            "suggested_position": round(suggested_position, 1),
            "is_etf_or_fund": True,
            "fund_type": fund_type
        }
    
    risk_score = 0 # 0-10分，越高风险越大
    risk_flags = []
    
    # --- 1. G=B+M 模型检测 ---
    
    # M (情绪) 检测: 估值过热
    # 优先使用PE分位点判断（如果可用），否则使用绝对PE值
    pe = data.get('pe', 0)
    pe_percentile = data.get('pe_percentile')
    
    if pe > 0:
        # 如果PE分位点可用，使用分位点判断
        if pe_percentile is not None and pe_percentile > 90:
            risk_score += 3
            risk_flags.append(f"M: 估值过热 (PE分位点{pe_percentile:.1f}%，处于历史高位)")
        elif pe_percentile is not None and pe_percentile > 80:
            risk_score += 2
            risk_flags.append(f"M: 估值偏高 (PE分位点{pe_percentile:.1f}%)")
        # 如果没有分位点数据，回退到绝对PE值
        elif pe_percentile is None:
            # 注意：PE为0可能是因为亏损，但不代表公司一定不好（可能是成长期的科技公司）
            # 需要综合判断营收增长、市值、行业等因素
            if pe > 60 and data['growth'] < 0.3:
                risk_score += 3
                risk_flags.append("M: 估值过高且增长不匹配 (PE>60)")
            elif pe > 40:
                risk_score += 1
    elif pe == 0 or pe is None:
        # PE为0或缺失，需要综合判断
        growth = data.get('growth', 0)
        market_cap = data.get('market_cap', 0)
        
        # 如果营收增长良好（>15%）且市值较大（>10亿），可能是成长期公司，风险适中
        if growth > 0.15 and market_cap > 1e9:
            risk_score += 1
            risk_flags.append("M: PE为0（亏损），但营收增长良好，可能处于成长期")
        # 如果营收负增长或市值很小，风险较高
        elif growth < 0 or (market_cap > 0 and market_cap < 1e8):
            risk_score += 2
            risk_flags.append("M: PE为0（亏损），且基本面较弱")
        else:
            # 其他情况，中等风险
            risk_score += 1.5
            risk_flags.append("M: PE为0（亏损），需关注盈利转正时间")
        
    # B (基本面) 检测: 财务健康度
    if data['growth'] < 0:
        risk_score += 3
        risk_flags.append("B: 营收负增长 (衰退迹象)")
    if data['margin'] < 0.05:
        risk_score += 1
        risk_flags.append("B: 利润率极低 (<5%)")

    # 财报日风险检测（波动率事件 - Binary Event）
    earnings_dates = data.get('earnings_dates', [])
    if earnings_dates:
        from datetime import datetime
        today = datetime.now().date()
        for earnings_date in earnings_dates[:1]:  # 只检查最近一个财报日期
            try:
                earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                days_until = (earnings_dt - today).days
                if 0 <= days_until < 7:
                    risk_score += 1
                    risk_flags.append(f"财报日风险: 财报将在{earnings_date}发布（{days_until}天后），波动率风险极高，建议财报前3天避险")
                elif 7 <= days_until <= 14:
                    risk_score += 0.5
                    risk_flags.append(f"财报日风险: 财报将在{earnings_date}发布（{days_until}天后），建议提前规划")
            except:
                pass

    # 解禁期风险检测（供给侧冲击 - Lock-up Expiry）
    lockup_data = data.get('lockup_data', {})
    if lockup_data and lockup_data.get('days_until_lockup') is not None:
        days_until_lockup = lockup_data['days_until_lockup']
        if 0 <= days_until_lockup < 7:
            risk_score += 2.5
            lockup_date = lockup_data.get('lockup_expiry_date', '未知日期')
            risk_flags.append(f"解禁期风险: 解禁将在{lockup_date}到来（{days_until_lockup}天后），抛压风险极高，可能面临巨大抛压")
        elif 7 <= days_until_lockup <= 14:
            risk_score += 1.5
            lockup_date = lockup_data.get('lockup_expiry_date', '未知日期')
            risk_flags.append(f"解禁期风险: 解禁将在{lockup_date}到来（{days_until_lockup}天后），可能面临抛压")
        # 如果解禁期已过（days_until_lockup < 0），不增加风险分，但可以添加提示
        elif days_until_lockup < 0 and abs(days_until_lockup) <= 30:
            # 解禁期刚过，可能仍有抛压，但不增加风险分
            pass

    # 技术面 (趋势) - 投机风控
    if data['price'] < data['ma200']:
        risk_score += 2
        risk_flags.append("技术: 价格跌破200日均线 (熊市趋势)")
    
    # --- 2. 投资风格适配 ---
    
    # 风格特定的红线（考虑PE为0的情况）
    pe = data.get('pe', 0)
    if style == 'value':
        if pe > 25:
            risk_score += 2
            risk_flags.append("风格不符: 价值股 PE > 25")
        elif pe == 0 or pe is None:
            risk_score += 1.5
            risk_flags.append("风格不符: 价值风格不适合亏损公司（PE=0）")
    if style == 'growth' and data['growth'] < 0.15:
        # 对于成长风格，如果PE为0但营收增长良好，可以容忍
        if pe == 0 or pe is None:
            # PE为0但增长良好，符合成长风格的特征，不扣分
            if data['growth'] < 0.15:
                risk_score += 2
                risk_flags.append("风格不符: 成长股增速 < 15%")
        else:
            risk_score += 2
            risk_flags.append("风格不符: 成长股增速 < 15%")

    # --- 3. 仓位计算 ---
    
    # 确定风险等级
    risk_level = "低"
    if risk_score >= 6: risk_level = "极高 (建议观望)"
    elif risk_score >= 4: risk_level = "高"
    elif risk_score >= 2: risk_level = "中"
    
    # 基础仓位上限 (根据你的文档)
    base_caps = {
        'value': 10,    # 10%
        'growth': 15,   # 15%
        'quality': 20,  # 20%
        'momentum': 5   # 5%
    }
    max_cap = base_caps.get(style, 10)
    
    # 风险调整系数
    adjustment = 1.0
    if risk_score >= 6: adjustment = 0.0 # 极高风险不买
    elif risk_score >= 4: adjustment = 0.4
    elif risk_score >= 2: adjustment = 0.7
    
    # 价格相关调整系数（基于目标价格和当前价格的关系）
    # 注意：这里先计算基础仓位，价格调整会在API层进行
    price_adjustment = 1.0  # 默认值，将在API层根据目标价格调整
    
    suggested_position = max_cap * adjustment
    
    return {
        "score": risk_score,
        "level": risk_level,
        "flags": risk_flags,
        "suggested_position": round(suggested_position, 1),
        "is_etf_or_fund": False,
        "fund_type": None,
        "price_adjustment": price_adjustment  # 占位符，将在API层更新
    }

