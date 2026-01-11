为了将上述理论转化为可执行的信号，我们设计了四个量化评分模型。这些公式旨在对市场上的数千个期权合约进行“打分”，帮助交易者筛选出数学期望最高的交易机会。
3.1 公式一：卖出看跌期权推荐值 (Sell Put Recommendation Value, SPRV)
设计目标： 寻找高胜率、高年化回报、且处于高波动率环境下的Put合约。

$$SPRV = \underbrace{\left( \frac{\text{Premium}}{\text{Strike} \times 100} \times \frac{365}{\text{DTE}} \right)}_{\text{年化回报率}} \times \underbrace{(1 - |\Delta|)^{1.5}}_{\text{胜率加权}} \times \underbrace{\log_{10}(\text{IVR} + 10)}_{\text{波动率溢价}} \times L_{liq}$$
逻辑详解：
年化回报率因子： $\frac{\text{Premium}}{\text{Strike} \times 100}$ 计算的是单笔交易的绝对回报率。乘以 $\frac{365}{\text{DTE}}$ 将其年化，使得不同到期日的期权可以横向对比。例如，30天赚1%（年化12%）优于60天赚1.5%（年化9%）。
胜率加权 $(1 - |\Delta|)^{1.5}$： $1 - |\Delta|$ 近似代表期权到期归零的概率（POP）。引入指数1.5是为了非线性地惩罚高风险（高Delta）交易。我们更偏好稳健的现金流，而非赌博式的接盘。
波动率溢价 $\log_{10}(\text{IVR} + 10)$： IV Rank (IVR) 是判断期权贵贱的核心。我们使用对数函数来平滑极端值。当IVR从0升至50时，得分显著提升；但从50升至100时，边际得分递减，因为极高的IV往往伴随着基本面崩塌的风险（如财报暴雷）。
流动性因子 $L_{liq}$： 这是一个阶梯函数。
若 Bid-Ask Spread / Premium $\le 5\%$，则 $L_{liq} = 1.0$。
若 Bid-Ask Spread / Premium $> 10\%$，则 $L_{liq} = 0.5$。
理由： 宽点差意味着进出场成本高，直接吞噬理论优势 18。
应用： 选择 SPRV 得分最高的合约，通常会指向那些基本面稳健但短期受情绪面错杀、波动率虚高的标的。
3.2 公式二：卖出看涨期权推荐值 (Sell Call Recommendation Value, SCRV)
设计目标： 针对Covered Call策略，寻找能最大化时间价值衰减（Theta），同时保留一定股价上涨空间的合约。

$$SCRV = \underbrace{\left( \frac{\Theta \times 365}{\text{Stock Price}} \right)}_{\text{年化Theta收益}} \times \underbrace{\left( \frac{1}{\Delta} \right)}_{\text{防召回系数}} \times \underbrace{\left( 1 + \frac{\text{IVP}}{100} \right)}_{\text{高波奖励}} \times \underbrace{\left( \frac{\text{Strike} - \text{Current}}{\text{Current}} \right)}_{\text{上涨空间}}$$
逻辑详解：
年化Theta收益： 衡量每天通过时间衰减获得的“租金”占资产价值的比例。这是Covered Call的核心收入源 19。
防召回系数 $1/\Delta$： Sell Call最怕的是股价大涨导致股票被低价召回。Delta越高，被召回概率越大。取倒数意味着我们奖励低Delta（深虚值）的期权，鼓励保留股票的上涨潜力。
高波奖励 IVP： 使用IV Percentile (IVP)。当IVP高时，Call的价格包含更多泡沫，卖出更划算。
上涨空间： 直接奖励行权价距离当前价格更远的合约。这确保了在股票被召回前，投资者已经享受了一段可观的涨幅。
3.3 公式三：买入看涨期权推荐值 (Buy Call Recommendation Value, BCRV)
设计目标： 针对LEAPS（长期期权）或投机性看涨。目标是“以小博大”，寻找低波动率、高Gamma爆发力的机会。

$$BCRV = \underbrace{\frac{\Gamma}{\Theta}}_{\text{效率比率}} \times \underbrace{\left( \frac{100}{\text{IVR} + 1} \right)}_{\text{低波红利}} \times \underbrace{\Delta^2}_{\text{方向性杠杆}} \times \text{Vol}_{\text{score}}$$
逻辑详解：
效率比率 $\Gamma / \Theta$： 这是期权买方的“黄金比率”。Gamma代表当股价向有利方向移动时Delta增加的速度（利润加速），Theta是每天付出的时间成本。我们希望用最小的Theta损耗换取最大的Gamma爆发力 20。
低波红利： 与卖方相反，买方希望在IVR极低（期权便宜）时买入。公式中IVR位于分母，IVR越低，得分越高。这利用了波动率的均值回归特性——低波动率往往预示着未来的波动率扩张（Vega收益） 4。
方向性杠杆 $\Delta^2$： 对于做多策略，我们需要足够的Delta来捕捉股价涨幅。平方处理是为了极大地奖励高Delta（如0.70-0.80）的深度实值期权（类似持有正股），而惩罚低Delta的“彩票”期权。
$\text{Vol}_{\text{score}}$： 成交量得分。买方策略需要灵活进出，必须剔除日成交量低于500张的合约。

3.4 公式四：买入看跌期权推荐值 (Buy Put Recommendation Value, BPRV)
设计目标： 高效对冲或做空。寻找“性价比”最高的保险。

$$BPRV = \underbrace{\frac{|\Delta|}{\text{Premium}}}_{\text{对冲杠杆}} \times \underbrace{\text{VRP}_{neg}}_{\text{反向VRP}} \times \underbrace{(1 - \rho)}_{\text{相关性对冲}} \times \text{Skew}_{\text{factor}}$$
逻辑详解：
对冲杠杆 $|\Delta| / \text{Premium}$： 每一美元权利金能买到多少负Delta？这是衡量对冲性价比的最直接指标。通常深虚值（Deep OTM）Put此项得分最高，因为它们极其便宜，一旦发生黑天鹅事件，Gamma效应会让Delta瞬间飙升 21。
反向VRP： 寻找IV相对历史RV没有过分溢价的时刻。如果在极度恐慌时买Put（IVR=99），由于波动率回落（Vega Crush），即使股价下跌也可能亏损。
相关性对冲 $(1 - \rho)$： $\rho$ 是该标的与投资组合其余部分的Correlation。我们希望买入与现有持仓相关性低的资产的Put，或者直接买入大盘指数Put来对冲系统性风险。
偏度因子 $\text{Skew}_{\text{factor}}$： 衡量波动率偏度（Volatility Skew）。如果OTM Put的IV远高于ATM Put，说明市场已经极度看空，买入成本过高，得分降低。
