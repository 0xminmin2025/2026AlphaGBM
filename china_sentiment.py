"""
中国市场特有的情绪数据获取模块
使用 AkShare 获取A股/港股特有的政策、资金流、舆情数据
"""

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import time


def get_china_stock_sentiment(ticker_symbol, market='CN'):
    """
    获取A股/港股特有的情绪指标
    
    参数:
        ticker_symbol: 股票代码（如：600519、688795、00700）
        market: 市场类型 'CN' (A股) 或 'HK' (港股)
    
    返回:
        sentiment_data: 包含各种情绪指标的字典
    """
    sentiment_data = {
        'latest_news': [],
        'main_net_inflow': 0,
        'retail_net_inflow': 0,
        'dragon_tiger_list': None,  # 龙虎榜数据
        'news_keywords': [],  # 新闻关键词
        'policy_signals': [],  # 政策信号
        'market_type': market
    }
    
    try:
        # 提取纯数字代码（去掉后缀）
        code = ticker_symbol.replace('.SS', '').replace('.SZ', '').replace('.HK', '').strip()
        
        if market == 'CN':
            # A股数据处理
            if len(code) == 6:
                # 判断是上海还是深圳
                if code.startswith(('600', '601', '603', '688')):
                    market_code = 'sh'  # 上海
                elif code.startswith(('000', '001', '002', '300')):
                    market_code = 'sz'  # 深圳
                else:
                    market_code = 'sh'  # 默认
                
                try:
                    # 1. 获取个股新闻（东方财富）
                    # 注意：akshare的接口可能有变化，需要根据实际情况调整
                    news_df = ak.stock_news_em(symbol=code)
                    if not news_df.empty:
                        # 取最新的5条新闻
                        latest_news = news_df.head(5)
                        sentiment_data['latest_news'] = latest_news[['title', 'date']].to_dict('records') if 'title' in latest_news.columns else []
                        
                        # 提取关键词
                        if 'title' in latest_news.columns:
                            all_titles = ' '.join(latest_news['title'].astype(str))
                            sentiment_data['news_keywords'] = extract_policy_keywords(all_titles)
                except Exception as e:
                    print(f"获取A股新闻失败 {code}: {e}")
                
                try:
                    # 2. 获取资金流向（主力/散户）
                    flow_df = ak.stock_individual_fund_flow_rank(indicator="今日")
                    # 查找当前股票的资金流向
                    if not flow_df.empty and '代码' in flow_df.columns:
                        stock_flow = flow_df[flow_df['代码'] == code]
                        if not stock_flow.empty:
                            sentiment_data['main_net_inflow'] = float(stock_flow.iloc[0].get('主力净流入', 0) or 0)
                            sentiment_data['retail_net_inflow'] = float(stock_flow.iloc[0].get('散户净流入', 0) or 0)
                except Exception as e:
                    print(f"获取A股资金流向失败 {code}: {e}")
                
                try:
                    # 3. 获取龙虎榜数据（如果上榜）
                    dragon_tiger = ak.stock_lhb_detail_em(start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'), 
                                                           end_date=datetime.now().strftime('%Y%m%d'))
                    if not dragon_tiger.empty and '代码' in dragon_tiger.columns:
                        stock_lhb = dragon_tiger[dragon_tiger['代码'] == code]
                        if not stock_lhb.empty:
                            sentiment_data['dragon_tiger_list'] = {
                                'date': stock_lhb.iloc[0].get('上榜日期', ''),
                                'reason': stock_lhb.iloc[0].get('上榜理由', ''),
                                'buy_amount': float(stock_lhb.iloc[0].get('买入额', 0) or 0),
                                'sell_amount': float(stock_lhb.iloc[0].get('卖出额', 0) or 0)
                            }
                except Exception as e:
                    print(f"获取龙虎榜数据失败 {code}: {e}")
        
        elif market == 'HK':
            # 港股数据处理
            try:
                # 港股资金流向（南向资金）
                # 注意：akshare对港股的支持可能有限，这里先做框架
                hk_flow = ak.tool_trade_date_hist_sina()
                # 港股的具体资金流数据可能需要其他接口
                sentiment_data['hk_northbound'] = "待实现"  # 南向资金数据
            except Exception as e:
                print(f"获取港股数据失败 {code}: {e}")
    
    except Exception as e:
        print(f"获取中国市场情绪数据时出错: {e}")
    
    return sentiment_data


def get_china_macro_policy_signals():
    """
    获取宏观政策风向（财联社电报、证券时报等）
    
    返回:
        policy_data: 包含政策信号的字典
    """
    policy_data = {
        'important_news': [],  # 重要新闻
        'policy_keywords': [],  # 政策关键词
        'market_impact': 'neutral'  # 市场影响：positive/negative/neutral
    }
    
    try:
        # 获取财联社7x24小时电报
        cls_news = ak.stock_telegraph_cls()
        if not cls_news.empty and 'title' in cls_news.columns:
            # 筛选重要新闻（包含关键词）
            important_keywords = ['重磅', '突发', '立案', '央行', '证监会', '国务院', '印发', '规划', 
                                '降准', '降息', '加息', '政策', '监管', '处罚', '立案调查']
            
            for idx, row in cls_news.head(20).iterrows():
                title = str(row.get('title', ''))
                if any(keyword in title for keyword in important_keywords):
                    policy_data['important_news'].append({
                        'title': title,
                        'date': row.get('date', ''),
                        'keywords': [kw for kw in important_keywords if kw in title]
                    })
            
            # 分析市场影响
            positive_keywords = ['降准', '降息', '利好', '支持', '扶持', '增长', '复苏']
            negative_keywords = ['立案', '处罚', '监管', '调查', '风险', '警告', '收紧']
            
            all_titles = ' '.join(cls_news['title'].head(20).astype(str))
            positive_count = sum(1 for kw in positive_keywords if kw in all_titles)
            negative_count = sum(1 for kw in negative_keywords if kw in all_titles)
            
            if positive_count > negative_count + 2:
                policy_data['market_impact'] = 'positive'
            elif negative_count > positive_count + 2:
                policy_data['market_impact'] = 'negative'
    
    except Exception as e:
        print(f"获取宏观政策信号失败: {e}")
    
    return policy_data


def extract_policy_keywords(text):
    """
    从文本中提取政策关键词
    
    参数:
        text: 文本内容
    
    返回:
        关键词列表
    """
    policy_keywords = [
        '国务院', '央行', '证监会', '银保监会', '发改委', '财政部',
        '印发', '规划', '方案', '通知', '意见',
        '降准', '降息', '加息', 'MLF', 'LPR',
        '立案', '调查', '处罚', '监管',
        '利好', '利空', '扶持', '支持'
    ]
    
    found_keywords = []
    text_lower = text.lower()
    for keyword in policy_keywords:
        if keyword in text:
            found_keywords.append(keyword)
    
    return found_keywords


def calculate_china_sentiment_score(sentiment_data, policy_data):
    """
    基于中国市场特有数据计算情绪分数（0-10分）
    
    参数:
        sentiment_data: 个股情绪数据
        policy_data: 宏观政策数据
    
    返回:
        sentiment_score: 情绪分数（0-10）
        sentiment_adjustment: 情绪调整值（用于调整M分数）
    """
    sentiment_score = 5.0  # 基准分
    adjustments = []
    
    # 1. 主力资金流向分析
    main_inflow = sentiment_data.get('main_net_inflow', 0)
    if main_inflow > 100_000_000:  # 主力净流入超过1亿
        sentiment_score += 1.5
        adjustments.append('主力大幅净流入（+1.5分）')
    elif main_inflow > 50_000_000:  # 主力净流入超过5000万
        sentiment_score += 1.0
        adjustments.append('主力净流入（+1.0分）')
    elif main_inflow < -100_000_000:  # 主力大幅净流出
        sentiment_score -= 2.0
        adjustments.append('主力大幅净流出（-2.0分）')
    elif main_inflow < -50_000_000:  # 主力净流出
        sentiment_score -= 1.0
        adjustments.append('主力净流出（-1.0分）')
    
    # 2. 政策信号分析（权重最高）
    market_impact = policy_data.get('market_impact', 'neutral')
    if market_impact == 'positive':
        sentiment_score += 2.0
        adjustments.append('政策面利好（+2.0分）')
    elif market_impact == 'negative':
        sentiment_score -= 2.0
        adjustments.append('政策面利空（-2.0分）')
    
    # 3. 龙虎榜分析（游资炒作信号）
    dragon_tiger = sentiment_data.get('dragon_tiger_list')
    if dragon_tiger:
        buy_amount = dragon_tiger.get('buy_amount', 0)
        sell_amount = dragon_tiger.get('sell_amount', 0)
        if buy_amount > sell_amount * 1.5:
            sentiment_score += 1.0
            adjustments.append('龙虎榜游资大幅买入（+1.0分）')
        elif sell_amount > buy_amount * 1.5:
            sentiment_score -= 1.5
            adjustments.append('龙虎榜游资大幅卖出（-1.5分）')
    
    # 4. 新闻关键词分析
    policy_keywords = sentiment_data.get('news_keywords', [])
    positive_kw = ['利好', '扶持', '支持', '增长', '复苏']
    negative_kw = ['立案', '处罚', '监管', '调查']
    
    positive_count = sum(1 for kw in policy_keywords if any(p in kw for p in positive_kw))
    negative_count = sum(1 for kw in policy_keywords if any(n in kw for n in negative_kw))
    
    if positive_count > negative_count:
        sentiment_score += 0.5
        adjustments.append('新闻情绪偏正面（+0.5分）')
    elif negative_count > positive_count:
        sentiment_score -= 0.5
        adjustments.append('新闻情绪偏负面（-0.5分）')
    
    # 限制分数范围
    sentiment_score = max(0, min(10, sentiment_score))
    
    return sentiment_score, adjustments


def get_northbound_funds():
    """
    获取北向资金流向（外资买A股）
    这是A股市场的"聪明钱"指标
    
    返回:
        northbound_data: 北向资金数据
    """
    northbound_data = {
        'today_net_inflow': 0,  # 今日净流入
        'recent_3d_net_inflow': 0,  # 近3日净流入
        'trend': 'neutral'  # 趋势：increasing/decreasing/neutral
    }
    
    try:
        # 获取北向资金流向
        northbound_df = ak.tool_trade_date_hist_sina()
        # 注意：具体的北向资金接口可能需要根据akshare最新文档调整
        # 这里先做框架
        
        # 示例：获取最近3天的北向资金数据
        # northbound_recent = ak.stock_connect_szse_underlying_index_daily_em()
        
    except Exception as e:
        print(f"获取北向资金数据失败: {e}")
    
    return northbound_data


