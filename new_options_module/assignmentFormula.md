第二部分：科学计算行权概率——超越 Delta

很多交易者直接用 Delta 近似代表行权概率，这在粗略估算时够用，但不够严谨。为了进行科学的量化打分，我们需要计算真实的**接货概率 (Probability of Assignment)**。

### 2.1 核心公式：$N(d_2)$

在 Black-Scholes 模型中，Delta 实际上是 $N(d_1)$，而**期权到期变为实值（ITM）的真实概率是 $N(d_2)$**。

$$P(\text{Assignment}) = N(d_2) = N\left( \frac{\ln(S/K) + (r - \frac{\sigma^2}{2})T}{\sigma\sqrt{T}} \right)$$

**公式变量解析：**

- $S$: 标的资产当前价格 (Spot Price)
    
- $K$: 行权价 (Strike Price)
    
- $r$: 无风险利率 (Risk-free rate)
    
- $\sigma$: 隐含波动率 (Implied Volatility)
    
- $T$: 距离到期时间 (以年为单位)
    
- $N(\cdot)$: 标准正态分布的累积分布函数 (在 Excel 中为 `NORMSDIST`)
    

### 2.2 为什么不用 Delta？

- **Delta ($N(d_1)$)**：衡量的是期权价格对股价变动的敏感度。它包含了股价上涨时的幅度加权。
    
- **概率 ($N(d_2)$)**：纯粹衡量股价落在行权价之外的可能性。
    
- **结论**：对于虚值期权（OTM），$N(d_2)$ 通常略小于 Delta。使用 Delta 会略微高估风险，而 $N(d_2)$ 才是精准的“接盘概率”。
    