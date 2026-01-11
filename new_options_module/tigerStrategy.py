from tigeropen.common.consts import (Language, Market, BarPeriod, QuoteRight)    
  
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
import datetime
import logging
import sys
import time
import pandas as pd
from tigeropen.common.consts import BarPeriod, SecurityType, Market, Currency
from tigeropen.common.util.contract_utils import stock_contract
from tigeropen.common.util.order_utils import limit_order
from tigeropen.tiger_open_config import get_client_config
from tigeropen.trade.trade_client import TradeClient

# 纳斯达克 11支稳定币相关股票
UNIVERSE_NDX = ["CRCL","COIN","MSTR","MARA","CEP","PYPL","V","JPM","BAC","C","WFC"]

# 恒生 16支稳定币相关股票
UNIVERSE_HS = ["6060","2598","2888","9618","0863","00165","02598","06060","01499","01788","00376","00923","01810","09618","01428","00388"]

# 常量定义
HOLDING_NUM = 5
ORDERS_CHECK_MAX_TIMES = 10
REQUEST_SIZE = 50  # 每次请求的股票数量
TARGET_QUANTITY = "target_quantity"
PRE_CLOSE = "pre_close"
LATEST_PRICE = "latest_price"
MARKET_CAPITAL = "market_capital"
SYMBOL = "symbol"
WEIGHT = "weight"
TIME = "time"
CLOSE = "close"
DATE = "date"
LOT_SIZE = "lot_size"

def get_client_config():
    """获取客户端配置"""
    client_config = TigerOpenClientConfig(props_path='./tiger_openapi_config.properties') #按需修改config&token路径
    return client_config

def request(symbols, method, **kwargs):
    """
    分批请求数据
    :param symbols: 股票代码列表
    :param method: 请求方法
    :param kwargs: 其他参数
    :return: 合并后的DataFrame
    """
    symbols = list(symbols)
    result = pd.DataFrame()
    for i in range(0, len(symbols), REQUEST_SIZE):
        part = symbols[i:i + REQUEST_SIZE]
        quote = method(part, **kwargs)
        if isinstance(quote, pd.DataFrame):
            result = pd.concat([result, quote])
        # 避免请求频率过高
        time.sleep(0.5)
    return result

def get_quote(symbols):
    """获取股票简要信息"""
    quote = request(symbols, quote_client.get_stock_briefs)
    return quote.set_index(SYMBOL) if not quote.empty else quote

def get_trade_meta(symbols):
    """获取交易元数据"""
    metas = request(symbols, quote_client.get_trade_metas)
    return metas.set_index(SYMBOL) if not metas.empty else metas

def get_history(symbols, period=BarPeriod.DAY, days=200, batch_size=50) -> pd.DataFrame:
    """
    获取多支股票的历史数据
    :param symbols: 股票代码列表
    :param period: K线周期
    :param days: 需要获取的天数
    :param batch_size: 每次请求的天数
    :return: 包含历史数据的DataFrame
    """
    if not symbols:
        return pd.DataFrame()
    
    end_time = int(datetime.datetime.now().timestamp() * 1000)
    all_data = pd.DataFrame()
    
    # 先获取所有股票的第一批数据
    first_batch = request(symbols, quote_client.get_bars, 
                         period=period, 
                         end_time=end_time, 
                         limit=batch_size)
    
    if first_batch.empty:
        return all_data
    
    first_batch[DATE] = pd.to_datetime(first_batch[TIME], unit='ms').dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
    all_data = pd.concat([all_data, first_batch])
    
    # 计算剩余需要获取的数据量
    remaining_days = days - batch_size
    if remaining_days <= 0:
        all_data.set_index([DATE, SYMBOL], inplace=True)
        return all_data.sort_index()
    
    # 获取剩余数据
    end_time = min(first_batch[TIME])
    for _ in range(0, remaining_days, batch_size):
        current_limit = min(batch_size, remaining_days)
        batch = request(symbols, quote_client.get_bars, 
                       period=period, 
                       end_time=end_time, 
                       limit=current_limit)
        
        if batch.empty:
            break
            
        batch[DATE] = pd.to_datetime(batch[TIME], unit='ms').dt.tz_localize('UTC').dt.tz_convert('US/Eastern') #按需修改时间
        all_data = pd.concat([all_data, batch])
        end_time = min(batch[TIME])
        remaining_days -= current_limit
    
    all_data.set_index([DATE, SYMBOL], inplace=True)
    return all_data.sort_index()

# 初始化客户端
client_config = get_client_config()
quote_client = QuoteClient(client_config)

# 获取行情权限
try:
    permissions = quote_client.grab_quote_permission() 
    print("行情权限获取成功:", permissions)
except Exception as e:
    print("获取行情权限失败:", str(e))
    sys.exit(1)

symbols_to_query = UNIVERSE_NDX
print(f"开始获取 {len(symbols_to_query)} 支股票的历史数据...")

start_time = time.time()
history_data = get_history(symbols_to_query, days=200)
end_time = time.time()

print(f"数据获取完成，耗时 {end_time - start_time:.2f} 秒")
print("获取到的数据量:", len(history_data))
print("数据示例:")
print(history_data.head(10))

# 保存到CSV
history_data.to_csv('hs_stock_history_data.csv')