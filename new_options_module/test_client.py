from tigeropen.common.consts import (Language,        # 语言
                                Market,           # 市场
                                BarPeriod,        # k线周期
                                QuoteRight)       # 复权类型
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig

client_config = TigerOpenClientConfig(props_path='/Users/lewis/space/trading/tiger/tiger_openapi_config.properties')
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
stock_price = quote_client.get_stock_briefs(['AAPL'])

# 查询行情函数会返回一个包含当前行情快照的pandas.DataFrame对象，见返回示例。具体字段含义参见get_stock_briefs方法说明
print(stock_price)