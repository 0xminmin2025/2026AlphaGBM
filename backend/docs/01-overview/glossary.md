# AlphaGBM 术语表 / Glossary

本术语表为 AlphaGBM 股票/期权分析平台的双语（中英文）参考文档，按英文术语字母顺序排列。

| English Term | 中文 | Description |
|---|---|---|
| AlphaGBM (G=B+M) | 核心分析模型 | 平台核心模型，G = B + M，即 Gain（收益）= Business fundamentals（基本面）+ Market sentiment（市场情绪）。通过融合基本面分析与市场情绪量化，生成综合投资评分。 |
| ATR (Average True Range) | 平均真实波幅 | 衡量资产价格波动性的技术指标，反映一段时间内价格的平均波动幅度，常用于设置止损和仓位管理。 |
| ATM (At The Money) | 平价期权 | 期权行权价等于或接近标的资产当前市场价格的状态。参见 OTM/ATM/ITM。 |
| BCRV (Buy Call Recommendation Value) | 买入看涨推荐值 | AlphaGBM 模型输出的买入看涨期权（Long Call）推荐评分，数值越高表示买入看涨期权的信号越强。 |
| Black-Scholes | 布莱克-斯科尔斯模型 | 经典的期权定价数学模型，用于计算欧式期权的理论价格，是平台期权估值的基础模型之一。 |
| Bollinger Bands | 布林带 | 由中轨（移动平均线）和上下轨（标准差通道）组成的技术分析指标，用于判断价格的超买超卖区间和波动趋势。 |
| BPRV (Buy Put Recommendation Value) | 买入看跌推荐值 | AlphaGBM 模型输出的买入看跌期权（Long Put）推荐评分，数值越高表示买入看跌期权的信号越强。 |
| Credit Ledger | 额度台账 | 系统内部记录用户分析额度的消费、充值与余额变动的账本机制，用于精确追踪每笔额度的增减。 |
| Credit Pack | 加油包/额度充值 | 参见 Top-up / Credit Pack。 |
| DTE (Days to Expiration) | 距到期天数 | 期权合约距离到期日的剩余自然日天数，是影响期权时间价值和策略选择的关键参数。 |
| EV (Expected Value) | 期望值模型 | 基于概率加权的期望收益计算模型，用于评估期权交易策略的预期盈亏，辅助投资决策。 |
| Failover | 故障切换 | 系统高可用架构中的容错机制，当主数据源或服务不可用时，自动切换到备用数据源或服务以保证系统持续运行。 |
| Greeks (Delta, Gamma, Theta, Vega) | 期权希腊字母 | 描述期权价格对各风险因子敏感度的一组参数：Delta（标的价格敏感度）、Gamma（Delta 变化率）、Theta（时间衰减）、Vega（波动率敏感度）。 |
| ITM (In The Money) | 价内期权 | 期权具有内在价值的状态——看涨期权行权价低于标的价格，看跌期权行权价高于标的价格。参见 OTM/ATM/ITM。 |
| IV (Implied Volatility) | 隐含波动率 | 由期权市场价格反推得到的标的资产未来波动率预期，是期权定价和策略分析的核心输入参数。 |
| IV Rank | 隐含波动率百分位 | 当前 IV 在过去一段时间（通常为一年）IV 范围中的相对位置，用于判断当前 IV 水平是偏高还是偏低。 |
| LEAPS (Long-Term Equity Anticipation Securities) | 长期期权 | 到期日超过一年的长期股票期权合约，适合长线投资者用于替代持股或进行长期对冲。 |
| MACD (Moving Average Convergence Divergence) | 指数平滑异同移动平均线 | 基于快慢两条指数移动平均线之差的趋势跟踪动量指标，用于识别趋势方向和买卖信号。 |
| OTM (Out of The Money) | 价外期权 | 期权没有内在价值的状态——看涨期权行权价高于标的价格，看跌期权行权价低于标的价格。参见 OTM/ATM/ITM。 |
| OTM/ATM/ITM | 价外/平价/价内 | 描述期权行权价与标的资产当前价格关系的三种状态：价外（无内在价值）、平价（行权价接近市价）、价内（有内在价值）。 |
| PEG (Price/Earnings to Growth) | 市盈增长比 | 市盈率（P/E）与盈利增长率的比值，用于衡量股票估值相对于盈利增长的合理性。PEG < 1 通常被认为估值偏低。 |
| Proration | 按比例计费 | 订阅计费中的按比例折算机制，当用户在计费周期中途升级或降级订阅方案时，按实际使用天数折算费用差额。 |
| RSI (Relative Strength Index) | 相对强弱指标 | 衡量价格涨跌速度和幅度的动量振荡指标，取值 0-100，通常 RSI > 70 为超买、RSI < 30 为超卖。 |
| RV (Realized Volatility) | 已实现波动率 | 基于历史价格数据计算的实际波动率，常与隐含波动率（IV）对比以评估波动率风险溢价（VRP）。 |
| SCRV (Sell Call Recommendation Value) | 卖出看涨推荐值 | AlphaGBM 模型输出的卖出看涨期权（Short Call / Covered Call）推荐评分，数值越高表示卖出看涨期权的信号越强。 |
| SPRV (Sell Put Recommendation Value) | 卖出看跌推荐值 | AlphaGBM 模型输出的卖出看跌期权（Short Put / Cash-Secured Put）推荐评分，数值越高表示卖出看跌期权的信号越强。 |
| Subscription | 订阅 | 平台的付费订阅服务体系，用户通过订阅不同方案获取相应的分析额度和功能权限。 |
| Top-up / Credit Pack | 加油包/额度充值 | 在订阅方案之外单独购买的额外分析额度包，用于补充当月已用尽的分析次数。 |
| VRP (Volatility Risk Premium) | 波动率风险溢价 | 隐含波动率（IV）与已实现波动率（RV）之间的差值，反映市场为波动率风险支付的溢价，是期权卖方策略的核心依据。 |
| ZEBRA (Zero Extrinsic Back Ratio Spread) | 零外在价值比率价差 | 一种期权组合策略，通过构建特定比率的看涨价差来模拟持有股票的收益特征，同时将外在时间价值降至接近零，降低时间衰减风险。 |
