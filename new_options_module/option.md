期权
get_option_expirations 获取期权到期日
QuoteClient.get_option_expirations(symbols, market=None)

说明

获取期权到期日

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
symbols	list[str]	Yes	正股资产符号列表。对于香港合约，使用 get_option_symbols 提供的符号，格式为 "CODE.HK"
market	tigeropen.common.consts.Market	Yes	市场，US/HK:港股。
返回

pandas.DataFrame

各 column 的含义如下：

参量名	类型	描述
symbol	str	证券代码
date	str	到日期 YYYY-MM-DD 格式的字符串
timestamp	int	到期日，精确到毫秒的时间戳
period_tag	str	期权周期标签，m为月期权，w为周期权
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

expiration = quote_client.get_option_expirations(symbols=['AAPL'], market=Market.US)
#for HK contracts
#expirationHK = quote_client.get_option_expirations(symbols=["MET.HK"],market=Market.HK)
print(expiration.head())
返回示例


   symbol option_symbol        date      timestamp period_tag
0    AAPL          AAPL  2025-11-14  1763096400000          w
1    AAPL          AAPL  2025-11-21  1763701200000          m
2    AAPL          AAPL  2025-11-28  1764306000000          w
3    AAPL          AAPL  2025-12-05  1764910800000          w
4    AAPL          AAPL  2025-12-12  1765515600000          w
5    AAPL          AAPL  2025-12-19  1766120400000          m
** 关于指数的特殊期权符号 **

标普500 .SPX: 月度期权符号是 SPX, 周期权和季度期权的符号都是 SPXW
纳斯达克100 ： 月期权 NDX, 周期权 NDXP
VIX指数 : 月期权 VIX, 周期权: VIXW


get_option_briefs 获取期权实时行情
QuoteClient.get_option_briefs(identifiers, market=None, timezone=None)

说明

获取期权实时行情

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
identifiers	list[str]	Yes	正股资产符号列表。对于香港合约，使用 get_option_symbols 提供的符号，格式为 "CODE.HK"
market	tigeropen.common.consts.Market	Yes	市场，US:美股 HK:港股。
timezone	str	No	时区, 如 'US/Eastern', 'Asia/Hong_Kong'
返回

pandas.DataFrame

各 column 的含义如下：

字段	类型	说明
identifier	str	期权代码
symbol	str	股票代码
strike	str	行权价
bid_price	float	买盘价格
bid_size	int	买盘数量
ask_price	float	卖盘价格
ask_size	int	卖盘数量
latest_price	float	最新价格
latest_time	int	最新成交时间
volume	int	成交量
high	float	最高价
low	float	最低价
open	float	开盘价
pre_close	float	前一交易日收盘价
open_interest	int	未平仓量
open	float	开盘价
change	float	涨跌额
multiplier	int	乘数，美股期权默认100
rates_bonds	float	一年期美国国债利率，每天更新一次，如：0.0078 表示实际利率为：0.78%
put_call	str	方向 (PUT/CALL)
volatility	str	历史波动率
expiry	int	到期时间（毫秒，当天0点）
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

briefs = quote_client.get_option_briefs(['AAPL 230317C000135000'], market=Market.US)
# 港股期权
# briefs = quote_client.get_option_briefs(['TCH.HK 230317C000135000'], market=Market.HK)
返回示例

Text

           identifier symbol         expiry strike put_call  multiplier  ask_price     open  \ 
NVDA  260116C00100000   NVDA  1768539600000  100.0     CALL         100      79.05       65  \  

ask_size  bid_price  bid_size  pre_close  latest_price latest_time  volume  open_interest \
    78.0        178      78.7       78.2          None          36   84175          78.09 \

 high    low  rates_bonds volatility  change 
79.57  77.89     0.036165     29.29%    -0.5
get_option_chain 获取期权链
QuoteClient.get_option_chain(symbol, expiry, option_filter=None, return_greek_value=None, market=None, timezone=None, **kwargs)

说明

获取期权链

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
symbol	str	Yes	期权对应的股票代码
expiry	str或int	Yes	期权到期日，毫秒单位的数字时间戳或日期字符串，如 1705640400000 或 '2024-01-19'
option_filter	tigeropen.quote.domain.filter.OptionFilter	No	过滤参数，可选
return_greek_value	bool	No	是否返回希腊值
market	tigeropen.common.consts.Market	Yes	市场，支持 US/HK
timezone	str	No	时区，如 'US/Eastern', 'Asia/Hong_Kong'
过滤参数:

各筛选指标, 除去 in_the_money 属性外, 其他指标使用时均对应 _min 后缀(表示范围最小值) 或 _max 后缀(表示范围最大值) 的字段名, 如 delta_min, theta_max, 参见代码示例.

OptionFilter可筛选指标如下：

参数	类型	是否必填	描述
implied_volatility	float	No	隐含波动率, 反映市场预期的未来股价波动情况, 隐含波动率越高, 说明预期股价波动越剧烈.
in_the_money	bool	No	是否价内
open_interest	int	No	未平仓量, 每个交易日完结时市场参与者手上尚未平仓的合约数. 反映市场的深度和流动性.
delta	float	No	delta, 反映正股价格变化对期权价格变化对影响. 股价每变化1元, 期权价格大约变化 delta. 取值 -1.0 ~ 1.0
gamma	float	No	gamma, 反映正股价格变化对于delta的影响. 股价每变化1元, delta变化gamma.
theta	float	No	theta, 反映时间变化对期权价格变化的影响. 时间每减少一天, 期权价格大约变化 theta.
vega	float	No	vega, 反映波动率对期权价格变化的影响. 波动率每变化1%, 期权价格大约变化 vega.
rho	float	No	rho, 反映无风险利率对期权价格变化的影响. 无风险利率每变化1%, 期权价格大约变化 rho.
返回

pandas.DataFrame

字段名	类型	描述
identifier	str	期权代码
symbol	str	期权对应的正股代码
expiry	int	期权到期日，毫秒级别的时间戳
strike	float	行权价
put_call	str	期权的方向
multiplier	float	乘数
ask_price	float	卖价
ask_size	int	卖量
bid_price	float	买价
bid_size	int	买量
pre_close	float	前收价
latest_price	float	最新价
volume	int	成交量
open_interest	int	未平仓数量
implied_vol	float	隐含波动率
delta	float	delta
gamma	float	gamma
theta	float	theta
vega	float	vega
rho	float	rho
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

option_chain = quote_client.get_option_chain(symbol='AAPL', expiry='2019-01-18', market=Market.US)
# 港股期权
# option_chains = quote_client.get_option_chain(symbol='TCH.HK', expiry='2024-06-27', market='HK', return_greek_value=True)

print(option_chain)


# 可定义 OptionFilter 进行过滤
option_filter = OptionFilter(implied_volatility_min=0.5, implied_volatility_max=0.9, delta_min=0, delta_max=1,
                          open_interest_min=100, gamma_min=0.005, theta_max=-0.05, in_the_money=True)
option_chain = quote_client.get_option_chain('AAPL', '2023-01-20', option_filter=option_filter, market=Market.US)
print(option_chain)

# 也可直接用指标名称过滤
option_chain = quote_client.get_option_chain('AAPL', '2023-01-20', implied_volatility_min=0.5, open_interest_min=200, vega_min=0.1, rho_max=0.9, market=Market.US)
                                      
# 转换 expiry 时间格式
option_chain['expiry_date'] = pd.to_datetime(option_chain['expiry'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
返回示例


  symbol         expiry             identifier strike put_call  volume  latest_price  \       
0   AAPL  1689912000000  AAPL  230721C00095000   95.0     CALL       0         80.47        
1   AAPL  1689912000000  AAPL  230721C00100000  100.0     CALL       0         73.50       

pre_close  open_interest  multiplier  implied_vol     delta     gamma     theta      vega \
    80.47            117         100     0.989442  0.957255  0.001332 -0.061754  0.059986 \
    76.85            206         100     0.903816  0.955884  0.001497 -0.058678  0.060930 \

rho                    expiry_date
0.133840 2023-07-21 00:00:00-04:00
0.141341 2023-07-21 00:00:00-04:00
get_option_depth 获取期权深度行情
QuoteClient.get_option_depth(identifiers: list[str], market, timezone=None)

说明

获取期权的深度行情数据。支持持美国和香港市场期权

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
identifiers	list[str]	Yes	期权代码列表，如 ['AAPL 220128C000175000']. 格式说明
market	tigeropen.common.consts.Market	Yes	市场，US/HK
timezone	str	No	时区，默认值为 'US/Eastern'， 港股期权需要传 'Asia/Hong_Kong'
返回

dict

结构如下：

参量名	类型	描述
identifier	str	期权符号
asks	list[tuple]	卖盘信息
bids	list[tuple]	买盘信息
asks 和 bids 中的每一项为一个元组，元组的元素组成为 (price, volume, timestamp, code)

示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Market
from tigeropen.common.util.contract_utils import get_option_identifier
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

# 或 client_config = get_client_config(props_path='tiger_openapi_config.properties 文件的目录路径')
quote_client = QuoteClient(client_config)

identifier = 'AAPL 190104P00134000'
# 或由四要素生成
# identifier = get_option_identifier('AAPL', '20190104', 'PUT', 134)


result = quote_client.get_option_depth([identifier], market=Market.US)
print(result)
返回示例

单个标的


{'identifier': 'ADBE 240816C00560000', 
 'asks': [(18.3, 36, 1719852973090, 'PHLX'), (18.3, 19, 1719852973090, 'EDGX'), (18.3, 14, 1719852972660, 'MPRL'), (18.3, 14, 1719852972512, 'BOX'), (18.3, 13, 1719852973090, 'EMLD'), (18.3, 12, 1719852973090, 'MIAX'), (18.3, 11, 1719852969837, 'ISE'), (18.3, 10, 1719852973487, 'AMEX'), (18.3, 10, 1719852973090, 'CBOE'), (18.3, 7, 1719852973090, 'GEM'), (18.3, 7, 1719852969591, 'MCRY'), (18.3, 7, 1719852969585, 'BZX'), (18.3, 6, 1719852969647, 'NSDQ'), (18.3, 4, 1719852973525, 'ARCA'), (18.3, 3, 1719852972512, 'MEMX'), (18.3, 3, 1719852969818, 'C2'), (18.3, 2, 1719852973422, 'BX')], 
 'bids': [(17.9, 8, 1719852972512, 'BOX'), (17.9, 7, 1719852973487, 'AMEX'), (17.9, 6, 1719852973090, 'EMLD'), (17.9, 6, 1719852972660, 'MPRL'), (17.9, 6, 1719852969837, 'ISE'), (17.9, 5, 1719852973422, 'BX'), (17.9, 5, 1719852973090, 'PHLX'), (17.9, 5, 1719852969647, 'NSDQ'), (17.9, 5, 1719852969591, 'MCRY'), (17.9, 4, 1719852973090, 'EDGX'), (17.9, 4, 1719852973090, 'MIAX'), (17.9, 3, 1719852973525, 'ARCA'), (17.9, 2, 1719852973090, 'CBOE'), (17.9, 2, 1719852973090, 'GEM'), (17.9, 2, 1719852969818, 'C2'), (17.9, 1, 1719852969585, 'BZX'), (17.85, 6, 1719852972512, 'MEMX')]
}
多个标的


{'ADBE 240816C00560000': 
    {'identifier': 'ADBE 240816C00560000', 
     'asks': [(18.3, 36, 1719852973090, 'PHLX'), (18.3, 19, 1719852973090, 'EDGX'), (18.3, 14, 1719852972660, 'MPRL'), (18.3, 14, 1719852972512, 'BOX'), (18.3, 13, 1719852973090, 'EMLD'), (18.3, 12, 1719852973090, 'MIAX'), (18.3, 11, 1719852969837, 'ISE'), (18.3, 10, 1719852973487, 'AMEX'), (18.3, 10, 1719852973090, 'CBOE'), (18.3, 7, 1719852973090, 'GEM'), (18.3, 7, 1719852969591, 'MCRY'), (18.3, 7, 1719852969585, 'BZX'), (18.3, 6, 1719852969647, 'NSDQ'), (18.3, 4, 1719852973525, 'ARCA'), (18.3, 3, 1719852972512, 'MEMX'), (18.3, 3, 1719852969818, 'C2'), (18.3, 2, 1719852973422, 'BX')], 
     'bids': [(17.9, 8, 1719852972512, 'BOX'), (17.9, 7, 1719852973487, 'AMEX'), (17.9, 6, 1719852973090, 'EMLD'), (17.9, 6, 1719852972660, 'MPRL'), (17.9, 6, 1719852969837, 'ISE'), (17.9, 5, 1719852973422, 'BX'), (17.9, 5, 1719852973090, 'PHLX'), (17.9, 5, 1719852969647, 'NSDQ'), (17.9, 5, 1719852969591, 'MCRY'), (17.9, 4, 1719852973090, 'EDGX'), (17.9, 4, 1719852973090, 'MIAX'), (17.9, 3, 1719852973525, 'ARCA'), (17.9, 2, 1719852973090, 'CBOE'), (17.9, 2, 1719852973090, 'GEM'), (17.9, 2, 1719852969818, 'C2'), (17.9, 1, 1719852969585, 'BZX'), (17.85, 6, 1719852972512, 'MEMX')]}, 
 'ADBE 240816P00560000': 
    {'identifier': 'ADBE 240816P00560000', 
     'asks': [(17.45, 6, 1719863999000, 'BOX'), (17.45, 5, 1719863999000, 'EMLD'), (17.45, 5, 1719863999000, 'PHLX'), (17.45, 1, 1719863999000, 'CBOE'), (17.45, 1, 1719863999000, 'ISE'), (17.45, 1, 1719863999000, 'ARCA'), (17.45, 1, 1719863999000, 'MPRL'), (17.45, 1, 1719863999000, 'NSDQ'), (17.45, 1, 1719863999000, 'BX'), (17.45, 1, 1719863999000, 'C2'), (17.45, 1, 1719863999000, 'BZX'), (21.65, 4, 1719863999000, 'EDGX'), (22.0, 2, 1719863999000, 'AMEX'), (27.3, 1, 1719863999000, 'GEM'), (27.5, 1, 1719863999000, 'MIAX'), (28.0, 1, 1719863999000, 'MCRY'), (0.0, 0, 1719864000000, 'MEMX')], 
     'bids': [(17.05, 6, 1719863999000, 'ISE'), (17.05, 5, 1719863999000, 'BOX'), (17.05, 5, 1719863999000, 'PHLX'), (17.05, 3, 1719863999000, 'MCRY'), (17.05, 2, 1719863999000, 'ARCA'), (17.05, 2, 1719863999000, 'MPRL'), (17.05, 2, 1719863999000, 'NSDQ'), (17.05, 2, 1719863999000, 'BX'), (17.05, 2, 1719863999000, 'BZX'), (17.05, 1, 1719863999000, 'AMEX'), (17.05, 1, 1719863999000, 'CBOE'), (17.05, 1, 1719863999000, 'GEM'), (17.05, 1, 1719863999000, 'C2'), (15.6, 1, 1719863999000, 'EDGX'), (15.5, 1, 1719863999000, 'MIAX'), (11.95, 1, 1719863999000, 'EMLD'), (0.0, 0, 1719864000000, 'MEMX')]}
  }
get_option_trade_ticks 获取期权逐笔成交数据
QuoteClient.get_option_trade_ticks(identifiers)

说明

获取期权的逐笔成交数据

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
identifiers	list[str]	Yes	期权代码列表，如 ['AAPL 220128C000175000']. 格式说明
返回

pandas.DataFrame

结构如下：

参量名	类型	描述
symbol	str	期权对应的正股代码
expiry	str	期权到期时间， YYYY-MM-DD 格式的字符串
put_call	str	期权方向
strike	float	行权价
time	int	成交时间
price	float	成交价格
volume	int	成交量
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.util.contract_utils import get_option_identifier

from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

identifier =  'AAPL 190104P00134000'
# 或由四要素生成
# identifier = get_option_identifier('AAPL', '20190104', 'PUT', 134)


option_trade_ticks = quote_client.get_option_trade_ticks([identifier])
返回示例


                identifier symbol         expiry put_call  strike           time  price  volume
0    AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640701803177   9.38       9
1    AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640701803177   9.38       1
2    AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640701803846   9.46       7
3    AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640701806266   9.55       1
4    AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640701918302   9.08       1
..                     ...    ...            ...      ...     ...            ...    ...     ...
111  AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640722112754   8.91      25
112  AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640723067491   9.00       4
113  AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640723585351   8.85       4
114  AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640724302670   9.13       2
115  AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1640724600973   8.85       1
get_option_bars 获取期权K线数据
QuoteClient.get_option_bars(identifiers, begin_time=-1, end_time=4070880000000, period=BarPeriod.DAY, limit=None, sort_dir=None, market=None, timezone=None)

说明

获取期权k线数据

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
identifiers	list[str]	Yes	期权代码列表， 单次上限30只， 如 ['AAPL 220128C000175000']，格式说明
begin_time	str或int	Yes	开始时间，毫秒级时间戳或日期字符串，如 1643346000000 或 '2019-01-01'
end_time	str或int	Yes	结束时间，毫秒级时间戳或日期字符串，如 1643346000000 或 '2019-01-01'
period	tigeropen.common.consts.BarPeriod	No	k线类型， 取值范围(DAY:日K，ONE_MINUTE:1分钟，FIVE_MINUTES:5分钟，HALF_HOUR:30分钟，ONE_HOUR:60分钟)
limit	int	No	每个期权的返回k线数量
sort_dir	tigeropen.common.consts.SortDirection	No	排序顺序，枚举 ASC/DESC ,默认 ASC
market	tigeropen.common.consts.Market	Yes	市场，US:美股 HK:港股
timezone	str	No	时区，如 'US/Eastern', 'Asia/Hong_Kong'
返回

pandas.DataFrame

结构如下：

参量名	类型	描述
identifier	str	期权代码
symbol	str	期权对应的正股代码
expiry	int	到期日，毫秒级时间戳
put_call	str	期权方向
strike	float	行权价
time	int	Bar对应的时间，毫秒级时间戳
open	float	开盘价
high	float	最高价
low	float	最低价
close	float	收盘价
volume	int	成交量
open_interest	int	未平仓数量
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import BarPeriod, Market
from tigeropen.common.util.contract_utils import get_option_identifier
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

identifier =  'AAPL 190104P00134000'
# 或由四要素生成
# identifier = get_option_identifier('AAPL', '20190104', 'PUT', 134)

bars = quote_client.get_option_bars([identifier],period = BarPeriod.DAY, market=Market.US)
print(bars)

# 转换 time 时间格式
bars['expiry_date'] = pd.to_datetime(bars['expiry'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
bars['time_date'] = pd.to_datetime(bars['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
返回示例


           identifier symbol         expiry put_call  strike           time   open   high  \ 
AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1639026000000   8.92   9.80  \                  AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1639112400000   9.05  10.80  \   AAPL  220128C00175000   AAPL  1643346000000     CALL   175.0  1639371600000  11.70  12.50  \

 low  close  volume  open_interest               expiry_date                 time_date
8.00   8.20     364              0 2022-01-28 00:00:00-05:00 2021-12-09 00:00:00-05:00
7.80  10.80     277            177 2022-01-28 00:00:00-05:00 2021-12-10 00:00:00-05:00
8.72   8.75     304            328 2022-01-28 00:00:00-05:00 2021-12-13 00:00:00-05:00
get_option_timeline 获取期权分时数据
QuoteClient.get_option_timeline(self, identifiers: Union[str, list[str]], market:Optional[Union[Market, str]] = None, begin_time: Optional[Union[str, int]] = None, timezone: Optional[str] = None)

说明

获取期权的分时数据

请求频率

频率限制请参考：接口请求限制

参数

参数	类型	是否必填	描述
identifiers	list[str]	Yes	期权代码列表， 单次上限30只， 如 ['AAPL 220128C000175000']，格式说明
market	Market	Yes	市场，默认HK，目前仅支持HK
返回

字段	类型	说明
identifier	str	期权符号
symbol	str	股票代码
put_call	str	看多或看空（CALL/PUT）
expiry	int	到期时间
strike	str	行权价
pre_close	float	昨日收盘价
volume	int	成交量
avg_price	double	平均成交价格
price	double	最新价格
time	int	当前分时时间
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import BarPeriod, Market
from tigeropen.common.util.contract_utils import get_option_identifier
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

identifier =  'TCH.HK 250929C00510000'
# 或由四要素生成
# identifier = get_option_identifier('TCH.HK', '20190104', 'PUT', 134)

result = quote_client.get_option_timeline([identifier], market=Market.HK)
print(result)
返回示例


                identifier  symbol         expiry put_call  strike  pre_close  price  \
0    TCH.HK250929C00510000  TCH.HK  1759075200000     CALL  510.00      29.36  29.36  \
1    TCH.HK250929C00510000  TCH.HK  1759075200000     CALL  510.00      29.36  29.36  \
2    TCH.HK250929C00510000  TCH.HK  1759075200000     CALL  510.00      29.36  29.36  \

avg_price           time  volume
29.360000  1750901400000       0
29.360000  1750901460000       0
29.360000  1750901520000       0
get_option_symbols 获取港股期权代码
QuoteClient.get_option_symbols(market = Market.HK, lang = Language.en_US)

说明

获取港股期权的代码, 比如 00700 的代码为 TCH.HK

请求频率

频率限制请参考：接口请求限制

参数

参量名	类型	是否必填	描述
market	tigeropen.common.consts.Market	No	Market.HK
lang	Language	No	返回信息的语言，非必填，默认为英文
返回

pandas.DataFrame

结构如下：

参量名	类型	描述
symbol	str	期权代码，如 TCH.HK
name	str	名称
underlying_symbol	str	港股股票代码 如 00700
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.util.contract_utils import get_option_identifier
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

result = quote_client.get_option_symbols()
print(result)
返回示例


     symbol name underlying_symbol
0    ALC.HK  ALC             02600
1    CRG.HK  CRG             00390
2    PAI.HK  PAI             02318
3    XCC.HK  XCC             00939
4    XTW.HK  XTW             00788
5    SHL.HK  SHL             00968
6    GHL.HK  GHL             00868
7    HEX.HK  HEX             00388
8    ACC.HK  ACC             00914
9    STC.HK  STC             02888