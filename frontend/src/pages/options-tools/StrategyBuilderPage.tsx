/**
 * 策略构建器 + Greeks 仪表盘
 * 设计参考：stitch/options_calculator_greeks
 */

import { useState } from 'react';
import api from '@/lib/api';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart
} from 'recharts';
import {
  Calculator, Plus, Trash2, Loader2, ArrowUpDown,
  TrendingUp, Clock, Waves
} from 'lucide-react';

interface StrategyBuilderPageProps {
  userTier: string;
}

interface LegInput {
  id: number;
  action: 'buy' | 'sell';
  option_type: 'call' | 'put';
  strike: string;
  expiry_days: string;
  iv: string;
  quantity: string;
}

const TEMPLATES = [
  { id: 'bull_call_spread', label: '牛市价差' },
  { id: 'bear_put_spread', label: '熊市价差' },
  { id: 'iron_condor', label: '铁鹰' },
  { id: 'straddle', label: '跨式' },
  { id: 'strangle', label: '宽跨式' },
  { id: 'covered_call', label: '备兑' },
  { id: 'protective_put', label: '保护性Put' },
  { id: 'collar', label: '领口' },
];

let nextId = 1;

function createLeg(overrides?: Partial<LegInput>): LegInput {
  return {
    id: nextId++,
    action: 'buy',
    option_type: 'call',
    strike: '',
    expiry_days: '30',
    iv: '25',
    quantity: '1',
    ...overrides,
  };
}

export default function StrategyBuilderPage({ userTier: _userTier }: StrategyBuilderPageProps) {
  const [spot, setSpot] = useState('');
  const [legs, setLegs] = useState<LegInput[]>([
    createLeg({ action: 'buy', option_type: 'call' }),
    createLeg({ action: 'sell', option_type: 'call' }),
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);

  const addLeg = () => {
    setLegs([...legs, createLeg()]);
  };

  const removeLeg = (id: number) => {
    if (legs.length <= 1) return;
    setLegs(legs.filter(l => l.id !== id));
  };

  const updateLeg = (id: number, field: keyof LegInput, value: string) => {
    setLegs(legs.map(l => l.id === id ? { ...l, [field]: value } : l));
  };

  // 使用模板
  const applyTemplate = async (templateId: string) => {
    if (!spot || parseFloat(spot) <= 0) {
      setError('请先输入标的价格');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const spotVal = parseFloat(spot);
      // 生成 strikes 列表
      const step = spotVal > 100 ? 5 : spotVal > 50 ? 2.5 : 1;
      const strikes: number[] = [];
      for (let s = spotVal - step * 5; s <= spotVal + step * 5; s += step) {
        strikes.push(Math.round(s * 100) / 100);
      }

      const res = await api.post('/options/tools/strategy/build', {
        mode: 'template',
        template_id: templateId,
        spot: spotVal,
        expiry_days: 30,
        strikes,
      });

      if (res.data?.success) {
        setResult(res.data.data);
        // 更新 legs UI
        const apiLegs = res.data.data.legs || [];
        setLegs(apiLegs.map((l: any) => createLeg({
          action: l.action,
          option_type: l.option_type,
          strike: String(l.strike),
          expiry_days: String(l.expiry_days),
          iv: l.iv ? String(Math.round(l.iv * 100)) : '25',
          quantity: String(l.quantity || 1),
        })));
      } else {
        setError(res.data?.error || '构建失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 自定义计算
  const calculate = async () => {
    if (!spot || parseFloat(spot) <= 0) {
      setError('请输入标的价格');
      return;
    }

    const invalidLeg = legs.find(l => !l.strike || parseFloat(l.strike) <= 0);
    if (invalidLeg) {
      setError('所有腿的行权价必须大于 0');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const res = await api.post('/options/tools/strategy/build', {
        mode: 'custom',
        spot: parseFloat(spot),
        legs: legs.map(l => ({
          action: l.action,
          option_type: l.option_type,
          strike: parseFloat(l.strike),
          expiry_days: parseInt(l.expiry_days) || 30,
          iv: (parseFloat(l.iv) || 25) / 100,
          quantity: parseInt(l.quantity) || 1,
        })),
      });

      if (res.data?.success) {
        setResult(res.data.data);
      } else {
        setError(res.data?.error || '计算失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  const greeks = result?.greeks;
  const pnl = result?.pnl;
  const chars = result?.characteristics;

  // P/L 图表数据
  const chartData = pnl ? pnl.prices.map((price: number, i: number) => ({
    price,
    pnl: pnl.pnl_at_expiry[i],
    current: pnl.pnl_current[i],
  })) : [];

  return (
    <div className="space-y-6">
      {/* 快速模板 */}
      <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
          <div className="w-full sm:w-48">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">标的价格 ($)</label>
            <input
              type="number"
              value={spot}
              onChange={(e) => setSpot(e.target.value)}
              placeholder="如 150.00"
              className="w-full bg-[#131315] text-[#fafafa] text-sm px-3 py-2 rounded-lg
                border-none outline-none focus:ring-1 focus:ring-[#66d8d3]/50 font-mono"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">快速模板</label>
            <div className="flex flex-wrap gap-2">
              {TEMPLATES.map(t => (
                <button
                  key={t.id}
                  onClick={() => applyTemplate(t.id)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg
                    bg-[#222224] text-[#bcc9c8] hover:bg-[#2a2a2c] hover:text-[#fafafa]
                    transition-colors disabled:opacity-50"
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 主体：双栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-6">
        {/* 左栏：腿构建 + P/L */}
        <div className="space-y-4">
          {/* 腿表格 */}
          <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-[#fafafa]">期权腿</h2>
              <button
                onClick={addLeg}
                className="flex items-center gap-1 text-xs text-[#66d8d3] hover:text-[#4edea3] transition-colors"
              >
                <Plus size={14} /> 添加腿
              </button>
            </div>

            <div className="space-y-2">
              {/* 表头 */}
              <div className="grid grid-cols-[80px_80px_1fr_80px_70px_60px_32px] gap-2 text-xs text-[#6b7280] font-medium">
                <span>方向</span>
                <span>类型</span>
                <span>行权价</span>
                <span>到期(天)</span>
                <span>IV(%)</span>
                <span>数量</span>
                <span></span>
              </div>

              {legs.map(leg => (
                <div key={leg.id} className="grid grid-cols-[80px_80px_1fr_80px_70px_60px_32px] gap-2 items-center">
                  <select
                    value={leg.action}
                    onChange={(e) => updateLeg(leg.id, 'action', e.target.value)}
                    className={`text-xs px-2 py-1.5 rounded-md border-none outline-none font-medium
                      ${leg.action === 'buy'
                        ? 'bg-[#4edea3]/10 text-[#4edea3]'
                        : 'bg-[#ffb4ab]/10 text-[#ffb4ab]'
                      }`}
                  >
                    <option value="buy">买入</option>
                    <option value="sell">卖出</option>
                  </select>

                  <select
                    value={leg.option_type}
                    onChange={(e) => updateLeg(leg.id, 'option_type', e.target.value)}
                    className="text-xs bg-[#222224] text-[#fafafa] px-2 py-1.5 rounded-md border-none outline-none"
                  >
                    <option value="call">CALL</option>
                    <option value="put">PUT</option>
                  </select>

                  <input
                    type="number"
                    value={leg.strike}
                    onChange={(e) => updateLeg(leg.id, 'strike', e.target.value)}
                    placeholder="行权价"
                    className="bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none outline-none font-mono"
                  />
                  <input
                    type="number"
                    value={leg.expiry_days}
                    onChange={(e) => updateLeg(leg.id, 'expiry_days', e.target.value)}
                    className="bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none outline-none font-mono"
                  />
                  <input
                    type="number"
                    value={leg.iv}
                    onChange={(e) => updateLeg(leg.id, 'iv', e.target.value)}
                    className="bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none outline-none font-mono"
                  />
                  <input
                    type="number"
                    value={leg.quantity}
                    onChange={(e) => updateLeg(leg.id, 'quantity', e.target.value)}
                    className="bg-[#131315] text-[#fafafa] text-xs px-2 py-1.5 rounded-md border-none outline-none font-mono"
                  />
                  <button
                    onClick={() => removeLeg(leg.id)}
                    className="text-[#6b7280] hover:text-[#ffb4ab] transition-colors p-1"
                    disabled={legs.length <= 1}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={calculate}
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-sm font-medium transition-all
                bg-gradient-to-r from-[#66d8d3] to-[#1da19d] text-[#131315]
                hover:shadow-[0_0_20px_rgba(102,216,211,0.3)]
                disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Calculator size={16} />}
              计算策略
            </button>

            {error && (
              <div className="text-xs text-[#ffb4ab] bg-[#ffb4ab]/10 px-3 py-2 rounded-lg">{error}</div>
            )}
          </div>

          {/* 策略摘要 */}
          {greeks && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <SummaryCard
                label="净成本"
                value={`$${greeks.net_cost?.toLocaleString()}`}
                sub={greeks.net_cost > 0 ? '借方' : '贷方'}
                color={greeks.net_cost > 0 ? '#ffb4ab' : '#4edea3'}
              />
              <SummaryCard
                label="最大收益"
                value={`$${greeks.max_profit?.toLocaleString()}`}
                sub={greeks.net_cost !== 0 ? `${Math.round((greeks.max_profit / Math.abs(greeks.net_cost)) * 100)}% ROI` : ''}
                color="#4edea3"
              />
              <SummaryCard
                label="最大亏损"
                value={`$${greeks.max_loss?.toLocaleString()}`}
                color="#ffb4ab"
              />
              <SummaryCard
                label="盈亏平衡"
                value={greeks.breakevens?.length > 0 ? `$${greeks.breakevens[0]}` : '-'}
                sub="到期价格"
              />
            </div>
          )}

          {/* P/L 图表 */}
          {chartData.length > 0 && (
            <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6">
              <h3 className="text-sm font-medium text-[#fafafa] mb-4">盈亏图</h3>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2c" />
                    <XAxis
                      dataKey="price"
                      tick={{ fill: '#bcc9c8', fontSize: 10, fontFamily: 'ui-monospace' }}
                      axisLine={{ stroke: '#2a2a2c' }}
                    />
                    <YAxis
                      tick={{ fill: '#bcc9c8', fontSize: 10, fontFamily: 'ui-monospace' }}
                      axisLine={{ stroke: '#2a2a2c' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a1c',
                        border: '1px solid rgba(102,216,211,0.2)',
                        borderRadius: '0.5rem',
                        fontSize: '11px',
                        fontFamily: 'ui-monospace',
                      }}
                      formatter={(v: any, name: any) => [
                        `$${v?.toFixed(2)}`,
                        name === 'pnl' ? '到期P/L' : '当前P/L'
                      ]}
                    />
                    <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="3 3" />
                    <Area
                      type="monotone"
                      dataKey="pnl"
                      fill="rgba(78,222,163,0.08)"
                      stroke="none"
                    />
                    <Line type="monotone" dataKey="pnl" stroke="#4edea3" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="current" stroke="#66d8d3" strokeWidth={1.5} dot={false} strokeDasharray="5 3" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>

        {/* 右栏：Greeks 仪表盘 */}
        <div className="space-y-4">
          {greeks ? (
            <>
              {/* 聚合 Greeks */}
              <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
                <h2 className="text-sm font-medium text-[#fafafa]">聚合 Greeks</h2>
                <div className="grid grid-cols-2 gap-3">
                  <GreekCard
                    icon={<ArrowUpDown size={14} />}
                    label="Delta"
                    value={greeks.delta?.toFixed(2)}
                    sub="方向敞口"
                    pct={Math.min(100, Math.abs(greeks.delta) / 100 * 100)}
                  />
                  <GreekCard
                    icon={<TrendingUp size={14} />}
                    label="Gamma"
                    value={greeks.gamma?.toFixed(4)}
                    sub="Delta 稳定性"
                  />
                  <GreekCard
                    icon={<Clock size={14} />}
                    label="Theta"
                    value={`$${greeks.theta?.toFixed(2)}/天`}
                    sub="时间衰减"
                    negative={greeks.theta < 0}
                  />
                  <GreekCard
                    icon={<Waves size={14} />}
                    label="Vega"
                    value={`$${greeks.vega?.toFixed(2)}`}
                    sub="波动率敏感度"
                  />
                </div>
              </div>

              {/* 各腿明细 */}
              {greeks.legs?.length > 0 && (
                <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-3">
                  <h3 className="text-sm font-medium text-[#fafafa]">各腿 Greeks</h3>
                  <div className="space-y-1">
                    <div className="grid grid-cols-[1fr_60px_60px_60px] gap-2 text-xs text-[#6b7280]">
                      <span>腿</span>
                      <span className="text-right">Delta</span>
                      <span className="text-right">Theta</span>
                      <span className="text-right">Vega</span>
                    </div>
                    {greeks.legs.map((leg: any, i: number) => (
                      <div key={i} className="grid grid-cols-[1fr_60px_60px_60px] gap-2 text-xs py-1.5
                        border-t border-[#222224]/50">
                        <span className="font-mono text-[#fafafa]">
                          <span className={leg.action === 'buy' ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}>
                            {leg.action === 'buy' ? '买' : '卖'}
                          </span>
                          {' '}{leg.strike}{leg.option_type === 'call' ? 'C' : 'P'}
                        </span>
                        <span className="text-right font-mono text-[#fafafa]">{leg.delta?.toFixed(2)}</span>
                        <span className="text-right font-mono text-[#fafafa]">{leg.theta?.toFixed(2)}</span>
                        <span className="text-right font-mono text-[#fafafa]">{leg.vega?.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 策略特征 */}
              {chars && (
                <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-3">
                  <h3 className="text-sm font-medium text-[#fafafa]">策略特征</h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-[#bcc9c8]">方向</span>
                      <span className="text-[#fafafa]">{chars.direction_cn}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#bcc9c8]">时间衰减</span>
                      <span className={chars.time_decay === 'positive' ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}>
                        {chars.time_decay_cn}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#bcc9c8]">波动率影响</span>
                      <span className="text-[#fafafa]">{chars.vol_impact_cn}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#bcc9c8]">风险/收益比</span>
                      <span className="text-[#fafafa] font-mono">1:{chars.risk_reward_ratio}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#bcc9c8]">风险限定</span>
                      <span className={chars.limited_risk ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}>
                        {chars.limited_risk ? '有限风险' : '无限风险'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-[#1a1a1c] rounded-xl p-12 text-center space-y-3">
              <Calculator size={36} className="mx-auto text-[#2a2a2c]" />
              <p className="text-xs text-[#6b7280]">选择模板或自定义腿，点击计算</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── 子组件 ───

function SummaryCard({
  label, value, sub, color
}: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="bg-[#1a1a1c] rounded-xl p-3 space-y-1">
      <p className="text-xs text-[#bcc9c8]">{label}</p>
      <p className="text-lg font-bold font-mono" style={{ color: color || '#fafafa' }}>{value}</p>
      {sub && <p className="text-[10px] text-[#6b7280]">{sub}</p>}
    </div>
  );
}

function GreekCard({
  icon, label, value, sub, pct, negative
}: {
  icon: React.ReactNode; label: string; value: string; sub: string; pct?: number; negative?: boolean;
}) {
  return (
    <div className="bg-[#131315] rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-[#6b7280]">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className={`text-base font-bold font-mono ${negative ? 'text-[#ffb4ab]' : 'text-[#fafafa]'}`}>
        {value}
      </p>
      <p className="text-[10px] text-[#6b7280]">{sub}</p>
      {pct != null && (
        <div className="h-1 bg-[#222224] rounded-full overflow-hidden">
          <div className="h-full bg-[#66d8d3] rounded-full" style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
      )}
    </div>
  );
}
