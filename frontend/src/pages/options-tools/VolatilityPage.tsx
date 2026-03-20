/**
 * 波动率分析页面 - 2D 微笑 + 偏斜指标
 * 设计参考：stitch/vol_smile_2d + vol_surface_3d
 */

import { useState, useCallback } from 'react';
import api from '@/lib/api';
import { useAuth } from '@/components/auth/AuthProvider';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart, Legend
} from 'recharts';
import { Activity, TrendingUp, BarChart3, Loader2, Search, Lock } from 'lucide-react';

interface VolatilityPageProps {
  userTier: string;
}

interface SmileData {
  strikes: number[];
  call_ivs: (number | null)[];
  put_ivs: (number | null)[];
  call_volumes: number[];
  put_volumes: number[];
  underlying_price: number;
  atm_strike: number;
  skew_metrics: Record<string, any>;
  atm_snapshot: Record<string, any>;
  iv_stats: Record<string, any>;
}

export default function VolatilityPage({ userTier }: VolatilityPageProps) {
  const { user } = useAuth();
  const [symbol, setSymbol] = useState('AAPL');
  const [expiry, setExpiry] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [smileData, setSmileData] = useState<SmileData | null>(null);
  const [availableExpiries, setAvailableExpiries] = useState<string[]>([]);

  // 加载到期日列表
  const loadExpiries = useCallback(async () => {
    if (!symbol.trim()) return;
    setError('');
    try {
      const res = await api.get(`/options/expiries/${symbol.trim().toUpperCase()}`);
      const expiries = res.data?.expiries || res.data?.data?.expiries || [];
      setAvailableExpiries(expiries);
      if (expiries.length > 0 && !expiry) {
        setExpiry(expiries[0]);
      }
    } catch (err: any) {
      // 尝试从期权链接口获取
      setAvailableExpiries([]);
    }
  }, [symbol]);

  // 加载波动率微笑数据
  const loadSmile = useCallback(async () => {
    if (!symbol.trim() || !expiry) {
      setError('请输入标的代码并选择到期日');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/options/tools/vol-smile/${symbol.trim().toUpperCase()}`, {
        params: { expiry }
      });
      if (res.data?.success) {
        setSmileData(res.data.data);
      } else {
        setError(res.data?.error || '获取数据失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [symbol, expiry]);

  // 图表数据
  const chartData = smileData ? smileData.strikes.map((strike, i) => ({
    strike,
    callIV: smileData.call_ivs[i] ? (smileData.call_ivs[i]! * 100) : null,
    putIV: smileData.put_ivs[i] ? (smileData.put_ivs[i]! * 100) : null,
    volume: smileData.call_volumes[i] + smileData.put_volumes[i],
  })) : [];

  const isPremium = userTier !== 'free';

  return (
    <div className="space-y-6">
      {/* 控制栏 */}
      <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          {/* 标的输入 */}
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">标的代码</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="如 AAPL, SPY"
                className="flex-1 bg-[#131315] text-[#fafafa] text-sm px-3 py-2 rounded-lg
                  border-none outline-none focus:ring-1 focus:ring-[#66d8d3]/50
                  font-mono placeholder:text-[#6b7280]"
                onKeyDown={(e) => e.key === 'Enter' && loadExpiries()}
              />
              <button
                onClick={loadExpiries}
                className="px-3 py-2 bg-[#222224] text-[#bcc9c8] rounded-lg text-sm
                  hover:bg-[#2a2a2c] transition-colors"
              >
                <Search size={16} />
              </button>
            </div>
          </div>

          {/* 到期日选择 */}
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">到期日</label>
            <select
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              className="w-full bg-[#131315] text-[#fafafa] text-sm px-3 py-2 rounded-lg
                border-none outline-none focus:ring-1 focus:ring-[#66d8d3]/50 font-mono"
            >
              <option value="">选择到期日</option>
              {availableExpiries.map(exp => (
                <option key={exp} value={exp}>{exp}</option>
              ))}
            </select>
          </div>

          {/* 分析按钮 */}
          <button
            onClick={loadSmile}
            disabled={loading || !expiry}
            className="px-6 py-2 rounded-lg text-sm font-medium transition-all
              bg-gradient-to-r from-[#66d8d3] to-[#1da19d] text-[#131315]
              hover:shadow-[0_0_20px_rgba(102,216,211,0.3)]
              disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
            分析波动率
          </button>
        </div>

        {error && (
          <div className="text-sm text-[#ffb4ab] bg-[#ffb4ab]/10 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}
      </div>

      {/* 主体内容 */}
      {smileData && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
          {/* 左侧：微笑曲线 */}
          <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-[#fafafa]">
                  波动率微笑 <span className="text-[#66d8d3] font-mono text-base">{symbol}</span>
                </h2>
                <p className="text-xs text-[#bcc9c8] mt-0.5">到期日: {expiry}</p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#4edea3] rounded" /> Put IV
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#66d8d3] rounded" /> Call IV
                </span>
              </div>
            </div>

            <div className="h-[350px] sm:h-[420px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2c" />
                  <XAxis
                    dataKey="strike"
                    tick={{ fill: '#bcc9c8', fontSize: 11, fontFamily: 'ui-monospace' }}
                    axisLine={{ stroke: '#2a2a2c' }}
                    label={{ value: '行权价 ($)', position: 'bottom', offset: 0, fill: '#6b7280', fontSize: 11 }}
                  />
                  <YAxis
                    tick={{ fill: '#bcc9c8', fontSize: 11, fontFamily: 'ui-monospace' }}
                    axisLine={{ stroke: '#2a2a2c' }}
                    label={{ value: 'IV %', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a1c',
                      border: '1px solid rgba(102,216,211,0.2)',
                      borderRadius: '0.5rem',
                      backdropFilter: 'blur(12px)',
                      fontSize: '12px',
                      fontFamily: 'ui-monospace',
                    }}
                    formatter={(value: any, name: string) => {
                      const label = name === 'callIV' ? 'Call IV' : 'Put IV';
                      return [value ? `${value.toFixed(2)}%` : '-', label];
                    }}
                    labelFormatter={(label) => `行权价: $${label}`}
                  />
                  {smileData.underlying_price > 0 && (
                    <ReferenceLine
                      x={smileData.atm_strike}
                      stroke="#66d8d3"
                      strokeDasharray="5 5"
                      strokeOpacity={0.5}
                      label={{ value: 'ATM', position: 'top', fill: '#66d8d3', fontSize: 10 }}
                    />
                  )}
                  <Area
                    type="monotone"
                    dataKey="putIV"
                    fill="rgba(78, 222, 163, 0.05)"
                    stroke="none"
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="putIV"
                    stroke="#4edea3"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                    activeDot={{ r: 4, fill: '#4edea3' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="callIV"
                    stroke="#66d8d3"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                    activeDot={{ r: 4, fill: '#66d8d3' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 右侧：指标面板 */}
          <div className="space-y-4">
            {/* 偏斜指标 */}
            <MetricCard title="偏斜指标">
              <MetricRow
                label="25-Delta Put 偏斜"
                value={smileData.skew_metrics?.put_skew_25d != null
                  ? `${smileData.skew_metrics.put_skew_25d}%` : '-'}
              />
              <MetricRow
                label="Put-Call IV 比率"
                value={smileData.skew_metrics?.put_call_iv_ratio?.toFixed(2) || '-'}
              />
              <MetricRow
                label="偏斜百分位 (1Y)"
                value={smileData.skew_metrics?.skew_percentile_1y != null
                  ? `${smileData.skew_metrics.skew_percentile_1y}th` : '-'}
                bar={smileData.skew_metrics?.skew_percentile_1y}
              />
            </MetricCard>

            {/* ATM 快照 */}
            <MetricCard title="ATM 快照">
              <MetricRow
                label="ATM IV"
                value={smileData.atm_snapshot?.atm_iv != null
                  ? `${smileData.atm_snapshot.atm_iv}%` : '-'}
                highlight
              />
              <MetricRow
                label="ATM Call 价格"
                value={smileData.atm_snapshot?.call_price != null
                  ? `$${smileData.atm_snapshot.call_price}` : '-'}
              />
              <MetricRow
                label="ATM Put 价格"
                value={smileData.atm_snapshot?.put_price != null
                  ? `$${smileData.atm_snapshot.put_price}` : '-'}
              />
              <MetricRow
                label="跨式价格"
                value={smileData.atm_snapshot?.straddle_price != null
                  ? `$${smileData.atm_snapshot.straddle_price}` : '-'}
                highlight
              />
            </MetricCard>

            {/* IV 统计 */}
            <MetricCard title="IV Rank & Percentile">
              {smileData.iv_stats?.current_iv != null && (
                <MetricRow label="当前 IV" value={`${smileData.iv_stats.current_iv}%`} />
              )}
              {smileData.iv_stats?.iv_rank != null ? (
                <>
                  <MetricRow
                    label="IV Rank"
                    value={`${smileData.iv_stats.iv_rank}%`}
                    bar={smileData.iv_stats.iv_rank}
                  />
                  <MetricRow
                    label="IV Percentile"
                    value={`${smileData.iv_stats.iv_percentile}%`}
                    bar={smileData.iv_stats.iv_percentile}
                  />
                </>
              ) : (
                <p className="text-xs text-[#6b7280]">需要历史数据计算</p>
              )}
            </MetricCard>

            {/* Pro 锁定区域 */}
            {!isPremium && (
              <div className="bg-[#1a1a1c] rounded-xl p-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-[#131315]/80 backdrop-blur-sm flex items-center justify-center z-10">
                  <div className="text-center space-y-2">
                    <Lock size={20} className="mx-auto text-[#6b7280]" />
                    <p className="text-xs text-[#bcc9c8]">升级解锁最佳机会推荐</p>
                  </div>
                </div>
                <div className="opacity-30">
                  <h3 className="text-sm font-medium text-[#fafafa] mb-3">最佳机会</h3>
                  <div className="space-y-2">
                    <div className="h-4 bg-[#222224] rounded" />
                    <div className="h-4 bg-[#222224] rounded w-3/4" />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 空状态 */}
      {!smileData && !loading && !error && (
        <div className="bg-[#1a1a1c] rounded-xl p-12 text-center space-y-4">
          <Activity size={48} className="mx-auto text-[#2a2a2c]" />
          <div className="space-y-2">
            <p className="text-[#bcc9c8] text-sm">输入标的代码，开始波动率分析</p>
            <p className="text-[#6b7280] text-xs">支持 US 股票和 ETF，如 AAPL, SPY, NVDA</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── 子组件 ───

function MetricCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#1a1a1c] rounded-xl p-4 space-y-3">
      <h3 className="text-sm font-medium text-[#fafafa]">{title}</h3>
      <div className="space-y-2.5">{children}</div>
    </div>
  );
}

function MetricRow({
  label, value, highlight, bar
}: {
  label: string;
  value: string;
  highlight?: boolean;
  bar?: number;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-[#bcc9c8]">{label}</span>
        <span className={`text-sm font-mono ${highlight ? 'text-[#66d8d3]' : 'text-[#fafafa]'}`}>
          {value}
        </span>
      </div>
      {bar != null && (
        <div className="h-1 bg-[#222224] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#66d8d3] rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, bar))}%` }}
          />
        </div>
      )}
    </div>
  );
}
