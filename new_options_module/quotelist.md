通用
QuoteClient 说明
QuoteClient(client_config, logger=None, is_grab_permission=True)

在SDK中发起行情接口调用时，需要使用到QuoteClient，QuoteClient中封装了所有行情相关的API接口调用。

默认条件下，QuoteClient会自动进行行情权限抢占（is_grab_permission=True），为避免多次实例化导致频繁抢占触发限流，建议仅在一个模块的顶层创建 QuoteClient 实例，并在程序其他位置通过 import 引用这一实例，而不要在每个模块中重复实例化。如果需要自行控制行情权限抢占，可以把 is_grab_permission 设置为False。

grab_quote_permission 行情权限抢占
QuoteClient.grab_quote_permission()

说明

当同一账号在多台设备同时使用时，行情数据仅在主设备上返回。若需在其他设备上查看行情，需执行”行情权限抢占“，将当前设备设为主设备；若不切换设备，则无需进行此操作。

注： Python sdk 2.0.9 版本之后，QuoteClient 在初始化时默认已调用该接口并自动抢占权限。

没有抢占行情权限的设备请求实时行情时，将会得到如下错误：


code=4 msg=4000:permission denied(current device does not have permission)
参数

无

返回

list， 其中每一项为权限数据组成的 dict

dict数据格式如下：

KEY	VALUE
name	行情权限名称
expire_at	权限过期时间(-1为长期有效)
name字段枚举值说明：

name字段取值	说明
usQuoteBasic	美股L1行情权限
usStockQuoteLv2Totalview	美股L2行情权限
hkStockQuoteLv2	大陆地区用户赠送的港股L2权限
hkStockQuoteLv2Global	非大陆地区用户购买的港股L2权限
usOptionQuote	美股期权L1行情权限
CBOEFuturesQuoteLv2	芝加哥期权交易所L2权限
HKEXFuturesQuoteLv2	香港期货交易所L2权限
SGXFuturesQuoteLv2	新加坡交易所L2权限
OSEFuturesQuoteLv2	大阪交易所L2权限权限
权限内容可参考行情权限与限制

示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

permissions = quote_client.grab_quote_permission()
print(permissions)
返回示例

Python

[{'name': 'usStockQuote', 'expire_at': 1698767999000}, {'name': 'usStockQuoteLv2Arca', 'expire_at': 1698767999000}, {'name': 'usStockQuoteLv2Totalview', 'expire_at': 1698767999000}, {'name': 'hkStockQuoteLv2', 'expire_at': 1698767999000}, {'name': 'usOptionQuote', 'expire_at': 1698767999000}]
get_quote_permission 查询行情权限
QuoteClient.get_quote_permission()

说明

查询当前所拥有的行情权限

参数

无

返回

同grab_quote_permission 行情权限抢占

示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)

permissions = quote_client.get_quote_permission()
返回示例

Python

[{'name': 'usStockQuote', 'expire_at': 1698767999000}, {'name': 'usStockQuoteLv2Arca', 'expire_at': 1698767999000}, {'name': 'usStockQuoteLv2Totalview', 'expire_at': 1698767999000}, {'name': 'hkStockQuoteLv2', 'expire_at': 1698767999000}, {'name': 'usOptionQuote', 'expire_at': 1698767999000}]
get_kline_quota 历史行情额度
QuoteClient.get_kline_quota()

说明

根据用户等级统计用户已使用和剩余可订阅的 symbol 个数（同一股票的不同期权只占用一个symbol，其他规则可参考历史行情限制&订阅限制）

参数

参数	类型	是否必填	说明
with_details	bool	No	是否返回已请求的symbol详情，默认不返回
返回

list. 其中每一项如下

字段	类型	说明
used	int	已使用数量
remain	int	剩余数量
method	str	api接口（kline：股票K线； future_kline：期货K线； option_kline：期权K线； history_timeline：股票历史分时）
symbol_details	list[dict]	已使用的标的列表，包括每个标的的最后拉取时间
其中 symbol_details 每项如下：

字段	类型	说明
code	string	股票代码
last_request_timestamp	string	最后一次拉取的时间字符串
示例

Python

from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import TradingSession, Market
from tigeropen.common.consts.filter_fields import MultiTagField
from tigeropen.tiger_open_config import TigerOpenClientConfig
client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')

quote_client = QuoteClient(client_config)


result = quote_client.get_kline_quota()
print(result)
返回示例

JSON

[ {
  "remain" : 200,
  "used" : 0,
  "method" : "kline",
  "symbol_details" : [ ]
}, {
  "remain" : 20,
  "used" : 0,
  "method" : "future_kline",
  "symbol_details" : [ ]
}, {
  "remain" : 197,
  "used" : 3,
  "method" : "option_kline",
  "symbol_details" : [ {
    "code" : "TCH.HK",
    "last_request_timestamp" : "1750851341848"
  }, {
    "code" : "ALB.HK",
    "last_request_timestamp" : "1750851341848"
  }, {
    "code" : "LNI.HK",
    "last_request_timestamp" : "1750851341848"
  } ]
} ]