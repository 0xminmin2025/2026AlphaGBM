/**
 * P/L 模拟器页面
 * 设计参考：stitch/p_l_simulator
 */

import { useState } from 'react';
import api from '@/lib/api';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart, Legend
} from 'recharts';
import {
  TrendingUp, Loader2, Plus, Trash2, Sliders,
  ArrowUp, ArrowDown, Minus
} from 'lucide-react';

interface PnLSimulatorPageProps {
  userTier: string;
}

interface LegInput {
  id: number;
  action: 'buy' | 'sell';
  option_type: 'call' | 'put';
  strike: string;
  expiry_days: string;
  iv: string;
}

let nextId = 100;

export default function PnLSimulatorPage({ userTier }: PnLSimulatorPageProps) {
  const isPremium = userTier !== 'free';
  const [symbol, setSymbol] = useState('SPY');
  const [spot, setSpot] = useState('');
  const [legs, setLegs] = useState<LegInput[]>([
    { id: nextId++, action: 'sell', option_type: 'call', strike: '', expiry_days: '37', iv: '25' },
    { id: nextId++, action: 'sell', option_type: 'put', strike: '', expiry_days: '37', iv: '25' },
  ]);
  const [futureDay, setFutureDay] = useState(18);
  const [ivShift, setIvShift] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);
  const [scenario, setScenario] = useState<'bull' | 'base' | 'bear'>('base');

  const addLeg = () => setLegs([...legs, { id: nextId++, action: 'buy', option_type: 'call', strike: '', expiry_days: '37', iv: '25' }]);
  const removeLeg = (id: number) => legs.length > 1 && setLegs(legs.filter(l => l.id !== id));
  const updateLeg = (id: number, field: string, value: string) => {
    setLegs(legs.map(l => l.id === id ? { ...l, [field]: value } : l));
  };

  const simulate = async () => {
    const spotVal = parseFloat(spot);
    if (!spotVal || spotVal <= 0) { setError('请输入标的价格'); return; }
    if (legs.some(l => !l.strike || parseFloat(l.strike) <= 0)) { setError('所有腿需要行权价'); return; }

    setLoading(true);
    setError('');
    try {
      const res = await api.post('/options/tools/simulate', {
        symbol,
        spot: spotVal,
        legs: legs.map(l => ({
          action: l.action,
          option_type: l.option_type,
          strike: parseFloat(l.strike),
          expiry_days: parseInt(l.expiry_days) || 37,
          iv: (parseFloat(l.iv) || 25) / 100,
        })),
        future_day: futureDay,
        iv_shift: ivShift / 100,
        include_heatmap: isPremium,
      });

      if (res.data?.success) {
        setResult(res.data.data);
      } else {
        setError(res.data?.error || '模拟失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 图表数据
  const chartData = result ? result.prices.map((price: number, i: number) => ({
    price,
    expiry: result.pnl_at_expiry[i],
    today: result.pnl_today[i],
    future: result.pnl_future?.[i],
  })) : [];

  const totalDays = result?.total_days || parseInt(legs[0]?.expiry_days) || 37;

  return (
    <div className="space-y-6">
      {/* 输入区 */}
      <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="w-24">
            <label className="block text-xs text-[#bcc9c8] mb-1.5">标的</label>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-full bg-[#131315] text-[#fafafa] text-sm px-3 py-2 rounded-lg border-none outline-none font-mono focus:ring-1 focus:ring-[#66d8d3]/50" />
          </div>
          <div className="w-32">
            <label className="block text-xs text-[#bcc9c8] mb-1.5">现价 ($)</label>
            <input type="number" value={spot} onChange={(e) => setSpot(e.target.value)}
              placeholder="652.41"
              className="w-full bg-[#131315] text-[#fafafa] text-sm px-3 py-2 rounded-lg border-none outline-none font-mono focus:ring-1 focus:ring-[#66d8d3]/50" />
          </div>
          <button onClick={simulate} disabled={loading}
            className="px-6 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-[#66d8d3] to-[#1da19d] text-[#131315]
              hover:shadow-[0_0_20px_rgba(102,216,211,0.3)] disabled:opacity-50 flex items-center gap-2">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sliders size={16} />}
            运行模拟
          </button>
        </div>

        {/* 腿编辑 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#6b7280]">期权腿</span>
            <button onClick={addLeg} className="text-xs text-[#66d8d3] hover:text-[#4edea3] flex items-center gap-1">
              <Plus size={12} /> 添加
            </button>
          </div>
          {legs.map(leg => (
            <div key={leg.id} className="flex gap-2 items-center">
              <select value={leg.action} onChange={(e) => updateLeg(leg.id, 'action', e.target.value)}
                className={`text-xs px-2 py-1.5 rounded-md border-none w-16 ${leg.action === 'buy' ? 'bg-[#4edea3]/10 text-[#4edea3]' : 'bg-[#ffb4ab]/10 text-[#ffb4ab]'}`}>
                <option value="buy">买入</option>
                <option value="sell">卖出</option>
              </select>
              <select value={leg.option_type} onChange={(e) => updateLeg(leg.id, 'option_type', e.target.value)}
                className="text-xs bg-[#222224] text-[#fafafa] px-2 py-1.5 rounded-md border-none w-16">
                <option value="call">CALL</option>
                <option value="put">PUT</option>
              </select>
              <input type="number" value={leg.strike} onChange={(e) => updateLeg(leg.id, 'strike', e.target.value)}
                placeholder="行权价" className="flex-1 bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none font-mono" />
              <input type="number" value={leg.expiry_days} onChange={(e) => updateLeg(leg.id, 'expiry_days', e.target.value)}
                className="w-14 bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none font-mono" />
              <input type="number" value={leg.iv} onChange={(e) => updateLeg(leg.id, 'iv', e.target.value)}
                className="w-14 bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none font-mono" />
              <button onClick={() => removeLeg(leg.id)} disabled={legs.length <= 1}
                className="text-[#6b7280] hover:text-[#ffb4ab] p-1"><Trash2 size={12} /></button>
            </div>
          ))}
        </div>

        {error && <div className="text-xs text-[#ffb4ab] bg-[#ffb4ab]/10 px-3 py-2 rounded-lg">{error}</div>}
      </div>

      {/* 结果 */}
      {result && (
        <>
          {/* 头部信息条 */}
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="text-[#bcc9c8]">
              <span className="font-mono text-[#66d8d3]">{symbol}</span>
              {' '}现价 <span className="font-mono text-[#fafafa]">${parseFloat(spot).toFixed(2)}</span>
            </span>
            <span className="text-[#bcc9c8]">
              到期 <span className="font-mono text-[#fafafa]">{totalDays}</span> 天
            </span>
            <span className="text-[#4edea3] font-mono">
              最大收益 ${result.max_profit?.toLocaleString()}
            </span>
            <span className="text-[#ffb4ab] font-mono">
              最大亏损 ${result.max_loss?.toLocaleString()}
            </span>
          </div>

          {/* P/L 图 + 控制 */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
            {/* 图表 */}
            <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6">
              <div className="h-[350px] sm:h-[420px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 5, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2c" />
                    <XAxis dataKey="price" tick={{ fill: '#bcc9c8', fontSize: 10, fontFamily: 'ui-monospace' }}
                      axisLine={{ stroke: '#2a2a2c' }} />
                    <YAxis tick={{ fill: '#bcc9c8', fontSize: 10, fontFamily: 'ui-monospace' }}
                      axisLine={{ stroke: '#2a2a2c' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a1c',
                        border: '1px solid rgba(102,216,211,0.2)',
                        borderRadius: '0.5rem',
                        fontSize: '11px',
                        fontFamily: 'ui-monospace',
                      }}
                      formatter={(v: any, name: any) => {
                        const labels: Record<string, string> = { expiry: '到期P/L', today: '当前P/L', future: `第${futureDay}天P/L` };
                        return [`$${Number(v)?.toFixed(2)}`, labels[name] || name];
                      }}
                    />
                    <Legend
                      formatter={(value: string) => {
                        const labels: Record<string, string> = { expiry: '到期', today: '当前', future: `第${futureDay}天` };
                        return <span className="text-xs text-[#bcc9c8]">{labels[value] || value}</span>;
                      }}
                    />
                    <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="3 3" />
                    {result.breakevens?.map((be: number, i: number) => (
                      <ReferenceLine key={i} x={be} stroke="#66d8d3" strokeDasharray="4 4" strokeOpacity={0.5} />
                    ))}
                    <Area type="monotone" dataKey="expiry" fill="rgba(78,222,163,0.06)" stroke="none" />
                    <Line type="monotone" dataKey="expiry" stroke="#4edea3" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="today" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="5 3" />
                    {result.pnl_future && (
                      <Line type="monotone" dataKey="future" stroke="#66d8d3" strokeWidth={1.5} dot={false} strokeDasharray="2 2" />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 控制面板 */}
            <div className="space-y-4">
              {/* 时间滑块 */}
              <div className="bg-[#1a1a1c] rounded-xl p-4 space-y-3">
                <h3 className="text-xs text-[#bcc9c8] font-medium">未来 P/L 日期</h3>
                <input
                  type="range" min={0} max={totalDays} value={futureDay}
                  onChange={(e) => setFutureDay(parseInt(e.target.value))}
                  className="w-full accent-[#66d8d3]"
                />
                <div className="flex justify-between text-xs font-mono text-[#6b7280]">
                  <span>今天</span>
                  <span className="text-[#66d8d3]">第 {futureDay} 天</span>
                  <span>到期</span>
                </div>
              </div>

              {/* IV 偏移 */}
              <div className="bg-[#1a1a1c] rounded-xl p-4 space-y-3">
                <h3 className="text-xs text-[#bcc9c8] font-medium">IV 偏移</h3>
                <input
                  type="range" min={-20} max={20} value={ivShift}
                  onChange={(e) => setIvShift(parseInt(e.target.value))}
                  className="w-full accent-[#66d8d3]"
                />
                <p className="text-center text-sm font-mono text-[#fafafa]">
                  {ivShift > 0 ? '+' : ''}{ivShift}%
                </p>
              </div>

              {/* 场景按钮 */}
              <div className="bg-[#1a1a1c] rounded-xl p-4 space-y-3">
                <h3 className="text-xs text-[#bcc9c8] font-medium">场景分析</h3>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: 'bull' as const, label: '看涨', icon: ArrowUp, pct: '+10%' },
                    { key: 'base' as const, label: '基准', icon: Minus, pct: '0%' },
                    { key: 'bear' as const, label: '看跌', icon: ArrowDown, pct: '-10%' },
                  ].map(s => (
                    <button key={s.key}
                      onClick={() => setScenario(s.key)}
                      className={`flex flex-col items-center gap-1 py-2 rounded-lg text-xs transition-all
                        ${scenario === s.key
                          ? 'bg-[#66d8d3]/10 text-[#66d8d3] shadow-[0_0_10px_rgba(102,216,211,0.1)]'
                          : 'bg-[#222224] text-[#bcc9c8] hover:bg-[#2a2a2c]'}`}>
                      <s.icon size={14} />
                      <span>{s.label}</span>
                      <span className="font-mono text-[10px]">{s.pct}</span>
                    </button>
                  ))}
                </div>

                {/* 场景结果 */}
                {result.scenarios?.length > 0 && (
                  <div className="space-y-2 mt-2">
                    {result.scenarios.map((sc: any) => (
                      <div key={sc.name} className={`flex justify-between items-center text-xs py-1
                        ${sc.name === scenario ? 'text-[#fafafa]' : 'text-[#6b7280]'}`}>
                        <span>{sc.name_cn} ({sc.price_change_pct > 0 ? '+' : ''}{sc.price_change_pct}%)</span>
                        <span className={`font-mono ${sc.pnl >= 0 ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}`}>
                          ${sc.pnl.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 概率指标 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#1a1a1c] rounded-xl p-3 text-center">
                  <p className="text-xs text-[#bcc9c8]">盈利概率</p>
                  <p className="text-xl font-bold font-mono text-[#4edea3]">{result.probability_of_profit}%</p>
                </div>
                <div className="bg-[#1a1a1c] rounded-xl p-3 text-center">
                  <p className="text-xs text-[#bcc9c8]">期望收益</p>
                  <p className={`text-xl font-bold font-mono ${result.expected_value >= 0 ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}`}>
                    ${result.expected_value?.toLocaleString()}
                  </p>
                </div>
                <div className="bg-[#1a1a1c] rounded-xl p-3 text-center">
                  <p className="text-xs text-[#bcc9c8]">风险/收益比</p>
                  <p className="text-xl font-bold font-mono text-[#fafafa]">1:{result.risk_reward_ratio}</p>
                </div>
                <div className="bg-[#1a1a1c] rounded-xl p-3 text-center">
                  <p className="text-xs text-[#bcc9c8]">隐含波幅</p>
                  <p className="text-xl font-bold font-mono text-[#66d8d3]">${result.implied_move}</p>
                </div>
              </div>

              {/* 重新模拟按钮 */}
              <button onClick={simulate} disabled={loading}
                className="w-full py-2 rounded-lg text-xs font-medium bg-[#222224] text-[#bcc9c8]
                  hover:bg-[#2a2a2c] transition-colors flex items-center justify-center gap-2">
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Sliders size={14} />}
                重新模拟
              </button>
            </div>
          </div>
        </>
      )}

      {/* 空状态 */}
      {!result && !loading && (
        <div className="bg-[#1a1a1c] rounded-xl p-12 text-center space-y-3">
          <TrendingUp size={48} className="mx-auto text-[#2a2a2c]" />
          <p className="text-[#bcc9c8] text-sm">设置期权腿参数，运行 P/L 模拟</p>
          <p className="text-[#6b7280] text-xs">支持多腿策略、时间衰减、IV 变动场景分析</p>
        </div>
      )}
    </div>
  );
}
