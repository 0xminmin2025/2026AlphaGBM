USE Open API Python SDK

pip3 install tigeropen


API 相关配置
在正式请求接口前，需要完成API接口调用的相关配置。具体配置信息（包括tigerId，account，license等）可以在开发者信息页面查看。

共有两种配置方式：

方式一

使用配置文件。 在开发者网站导出配置文件 tiger_openapi_config.properties， 放入合适的系统路径，如 /Users/demo/props/ 然后将该路径填入TigerOpenClientConfig的 props_path 参数下（也可将配置文件放入程序的当前启动目录，sdk默认会取当前路径）。 使用这种方式，则不需要再代码中配置 tiger_id, account, private_key 等信息了。

此外。对于港股牌照，tiger_openapi_token.properties 是必须的，此文件也需放入 props_path指定的路径下。

Python

from tigeropen.common.consts import (Language,        # 语言
                                Market,           # 市场
                                BarPeriod,        # k线周期
                                QuoteRight)       # 复权类型
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient

def get_client_config():
    """
    https://quant.itigerup.com/#developer 开发者信息获取
    """
    # 港股牌照需用 props_path 参数指定token路径，如 '/Users/xxx/xxx/', 如不指定则取当前路径
    # 必须使用关键字参数指定 props_path
    client_config = TigerOpenClientConfig(props_path='/Users/demo/props/')
    return client_config

# 调用上方定义的函数生成用户配置ClientConfig对象
client_config = get_client_config()
方式二

以查询行情为例，所有行情接口的操作都通过QuoteClient对象的成员方法实现，所以调用相关行情接口之前需要先初始化QuoteClient，具体实现方式如下：

需要先生成client_config对象，对应以下示例的 client_config = get_client_config() ，然后把该client_config对象传入QuoteClient，来初始化QuoteClient，再调用QuoteClient具体的方法即可。TradeClient，PushClient 的初始化方式与此类似。

⚠️
CAUTION

以下示例中的read_private_key('填写私钥PEM文件的路径') 对应的PEM文件需要自行生成。先把开发者页面中的 PKCS#1 格式的私钥复制到本地文件中，再把该文件的完整路径填入这里即可(包含文件名)，例如路径：/data0/config/private_key.pem，在 private_key.pem中保存私钥即可。

Python

from tigeropen.common.consts import (Language,        # 语言
                                Market,           # 市场
                                BarPeriod,        # k线周期
                                QuoteRight)       # 复权类型
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient

def get_client_config():
    """
    https://quant.itigerup.com/#developer 开发者信息获取
    """
    client_config = TigerOpenClientConfig() 
    # 港股牌照需用 props_path 参数指定token路径，如 props_path='/Users/xxx/xxx/', 如不指定则取当前路径
    # client_config = TigerOpenClientConfig(props_path='.')
    client_config.private_key = read_private_key('填写私钥PEM文件的路径')
    client_config.tiger_id = '替换为tigerid'
    client_config.account = '替换为账户，建议使用模拟账户'
    client_config.license = 'TBSG' # license info
    #机构账户，添加用户密钥
    client_config.secret_key = '替换为用户密钥'
    client_config.language = Language.zh_CN  #可选，不填默认为英语'
    # client_config.timezone = 'US/Eastern' # 可选时区设置
    return client_config

# 调用上方定义的函数生成用户配置ClientConfig对象
client_config = get_client_config()

# 随后传入配置参数对象来初始化QuoteClient
quote_client = QuoteClient(client_config)

# 获取 00700 标的对应的行情数据
stock_price = quote_client.get_stock_briefs(['00700'])
ClientConfig 常用配置项介绍
各配置项可在 client_config = TigerOpenClientConfig() 实例化之后，通过client_config属性设置，如 client_config.timeout = 60

Python

# 开发者信息(推荐使用 props_path 的方式配置开发者信息)
client_config.tiger_id = 1
client_config.account = '123456'
client_config.license = 'TBSG'
client_config.private_key = read_private_key('私钥路径')  # 需 from tigeropen.common.util.signature_utils import read_private_key
# 私钥也可填字符内容
client_config.private_key = 'MIICWwIBAAKBgQCSW+.....私钥内容'

# 日志级别及路径
client_config.log_level = logging.DEBUG  # 需 import logging
client_config.log_path = '/tmp/tigerapi.log'

# 语言
client_config.language = 'zh_CN'
# 时区(如果配置了时区，涉及有时间字符串参数的接口，将会按当作该时区的时间。SDK默认不设置时区，服务端会当北京时间处理)
client_config.timezone = 'US/Eastern'

# 接口超时时间
client_config.timeout = 15
# 超时重试设置
# 最长重试时间，单位秒
client_config.retry_max_time = 60
# 最多重试次数
client_config.retry_max_tries = 5

# 2FA token 刷新间隔, 单位秒。设置为0则不自动刷新。 默认不刷新
client_config.token_refresh_duration = 24 * 60 * 60


基本功能示例
老虎Open API SDK提供了丰富的接口来调用老虎的服务，本章节将对老虎API的核心功能进行一一演示：包括查询行情，订阅行情，以及调用API进行交易

查询行情
以下为一个最简单的调用老虎API的示例，演示了如何调用Open API来主动查询股票行情。接下来的例子分别演示了如何调用Open API来进行交易与订阅行情。

除上述基础功能外，Open API还支持查询、交易多个市场的不同标的，以及其他复杂请求。对于其他Open API支持的接口和请求，请在快速入门后阅读文档正文获取列表及使用方法，并参考快速入门以及文档中的例子进行调用

为方便直接复制运行，以下的说明采用注释的形式

Python

from tigeropen.common.consts import (Language,        # 语言
                                Market,           # 市场
                                BarPeriod,        # k线周期
                                QuoteRight)       # 复权类型
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig

client_config = TigerOpenClientConfig(props_path='/path/to/your/properties/file/')
# anothor method 
# def get_client_config():
#    client_config = TigerOpenClientConfig()
#    # 如果是windowns系统，路径字符串前需加 r 防止转义， 如 read_private_key(r'C:\Users\admin\tiger.pem')
#    client_config.private_key = read_private_key('填写私钥PEM文件的路径')
#    client_config.tiger_id = '替换为tigerid'
#    client_config.account = '替换为账户，建议使用模拟账户'
#    client_config.language = Language.zh_CN  #可选，不填默认为英语'
#    # client_config.timezone = 'US/Eastern' # 可选时区设置
#    return client_config
# 调用上方定义的函数生成用户配置ClientConfig对象
# client_config = get_client_config()

# 随后传入配置参数对象来初始化QuoteClient
quote_client = QuoteClient(client_config)

# 完成初始化后，就可以调用quote_client方法来使用调用QuoteClient对象的get_stock_brief方法来查询股票行情

# 调用API查询股票行情
stock_price = quote_client.get_stock_briefs(['00700'])

# 查询行情函数会返回一个包含当前行情快照的pandas.DataFrame对象，见返回示例。具体字段含义参见get_stock_briefs方法说明
print(stock_price)
返回示例


  symbol  ask_price  ask_size  bid_price  bid_size  pre_close  latest_price  \
0  00700      326.4     15300      326.2     26100     321.80         326.4   

     latest_time    volume    open    high     low  status  
0  1547516984730   2593802  325.00  326.80  323.20  NORMAL 


I want to build a backend service, which can receive a stock symbol, and option expiration date, and return the option data, for both CALL and PUT.
Write a simple front web page to query the backend for the option data for demo.

make sure the backend API is friendly and easy to use.


 Before you really start write the backend service. You should try to init the client first with correct credentials. make sure the client is correct. read the doc. and then complete the option query service. 