/**
 * 期权机会扫描器页面
 * 设计参考：stitch/option_scanner
 */

import { useState } from 'react';
import api from '@/lib/api';
import {
  Search, Loader2, Lock, ChevronRight, BarChart3,
  Activity
} from 'lucide-react';

interface OptionScannerPageProps {
  userTier: string;
}

const STRATEGY_OPTIONS = [
  { value: 'covered_call', label: '备兑看涨 Covered Call' },
  { value: 'cash_secured_put', label: '现金担保看跌 Cash Secured Put' },
  { value: 'bull_call_spread', label: '牛市价差 Bull Call Spread' },
  { value: 'wheel', label: 'Wheel 策略' },
];

const EXPIRY_OPTIONS = [
  { value: 'weekly', label: '周期权' },
  { value: 'monthly', label: '月期权' },
  { value: '30-60d', label: '30-60天' },
];

function scoreColor(score: number): string {
  if (score >= 80) return '#4edea3';
  if (score >= 60) return '#66d8d3';
  if (score >= 40) return '#f59e0b';
  return '#ffb4ab';
}

export default function OptionScannerPage({ userTier }: OptionScannerPageProps) {
  const isPremium = userTier !== 'free';

  const [strategy, setStrategy] = useState('covered_call');
  const [expiryRange, setExpiryRange] = useState('monthly');
  const [ivMin, setIvMin] = useState(0);
  const [minYield, setMinYield] = useState('');
  const [tickers, setTickers] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState<any>(null);
  const [selectedRow, setSelectedRow] = useState<any>(null);

  const scan = async () => {
    setLoading(true);
    setError('');
    setSelectedRow(null);
    try {
      const payload: any = {
        strategies: [strategy],
        expiry_range: expiryRange,
        iv_percentile_min: ivMin,
        max_results: isPremium ? 50 : 5,
      };
      if (minYield) payload.min_yield_pct = parseFloat(minYield);
      if (tickers.trim()) payload.tickers = tickers.split(',').map(t => t.trim().toUpperCase());

      const res = await api.post('/options/tools/scan', payload);
      if (res.data?.success) {
        setResults(res.data.data);
      } else {
        setError(res.data?.error || '扫描失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  const scanResults = results?.results || [];

  return (
    <div className="space-y-6">
      {/* 筛选栏 */}
      <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          {/* 策略类型 */}
          <div className="min-w-[180px]">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">策略类型</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
              className="w-full bg-[#131315] text-[#fafafa] text-sm px-3 py-2 rounded-lg border-none outline-none focus:ring-1 focus:ring-[#66d8d3]/50">
              {STRATEGY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          {/* 到期范围 */}
          <div>
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">到期范围</label>
            <div className="flex gap-1">
              {EXPIRY_OPTIONS.map(o => (
                <button key={o.value}
                  onClick={() => setExpiryRange(o.value)}
                  className={`px-3 py-2 text-xs rounded-lg transition-colors
                    ${expiryRange === o.value
                      ? 'bg-[#66d8d3]/15 text-[#66d8d3]'
                      : 'bg-[#222224] text-[#bcc9c8] hover:bg-[#2a2a2c]'}`}>
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* IV 百分位 */}
          <div className="w-32">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">IV 百分位 ≥</label>
            <input type="range" min={0} max={100} value={ivMin}
              onChange={(e) => setIvMin(parseInt(e.target.value))}
              className="w-full accent-[#66d8d3]" />
            <p className="text-[10px] text-[#6b7280] text-center font-mono">{ivMin}%</p>
          </div>

          {/* 最低收益率 */}
          <div className="w-24">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">最低收益率%</label>
            <input type="number" value={minYield} onChange={(e) => setMinYield(e.target.value)}
              placeholder="1.0"
              className="w-full bg-[#131315] text-[#fafafa] text-xs px-3 py-2 rounded-lg border-none outline-none font-mono focus:ring-1 focus:ring-[#66d8d3]/50" />
          </div>

          {/* 自定义标的 */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs text-[#bcc9c8] mb-1.5 font-medium">标的 (逗号分隔，留空用默认)</label>
            <input value={tickers} onChange={(e) => setTickers(e.target.value)}
              placeholder="AAPL, NVDA, TSLA"
              className="w-full bg-[#131315] text-[#fafafa] text-xs px-3 py-2 rounded-lg border-none outline-none font-mono focus:ring-1 focus:ring-[#66d8d3]/50" />
          </div>

          {/* 扫描按钮 */}
          <button onClick={scan} disabled={loading}
            className="px-6 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-[#66d8d3] to-[#1da19d] text-[#131315]
              hover:shadow-[0_0_20px_rgba(102,216,211,0.3)] disabled:opacity-50 flex items-center gap-2 whitespace-nowrap">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            扫描
          </button>
        </div>

        {error && <div className="text-xs text-[#ffb4ab] bg-[#ffb4ab]/10 px-3 py-2 rounded-lg">{error}</div>}
      </div>

      {/* 结果区 */}
      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
          {/* 结果表格 */}
          <div className="bg-[#1a1a1c] rounded-xl p-4 sm:p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-[#fafafa]">
                扫描结果 <span className="text-[#6b7280] font-mono ml-2">{results.total_matches} 条匹配</span>
              </h2>
              <span className="text-[10px] text-[#6b7280]">{results.scan_time_ms}ms</span>
            </div>

            {/* 表头 */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[#6b7280] border-b border-[#222224]">
                    <th className="text-left py-2 px-2 font-medium">标的</th>
                    <th className="text-left py-2 px-2 font-medium">策略</th>
                    <th className="text-right py-2 px-2 font-medium">行权价</th>
                    <th className="text-left py-2 px-2 font-medium">到期</th>
                    <th className="text-right py-2 px-2 font-medium">权利金</th>
                    <th className="text-right py-2 px-2 font-medium">收益率%</th>
                    <th className="text-right py-2 px-2 font-medium">IV Rank</th>
                    <th className="text-right py-2 px-2 font-medium">Delta</th>
                    <th className="text-right py-2 px-2 font-medium">OTM%</th>
                    <th className="text-center py-2 px-2 font-medium">GBM</th>
                  </tr>
                </thead>
                <tbody>
                  {scanResults.map((row: any, i: number) => {
                    const isFreeLimit = !isPremium && i >= 5;
                    return (
                      <tr key={i}
                        onClick={() => !isFreeLimit && setSelectedRow(row)}
                        className={`border-b border-[#1a1a1c] cursor-pointer transition-colors
                          ${selectedRow === row ? 'bg-[#66d8d3]/5' : 'hover:bg-[#222224]/50'}
                          ${isFreeLimit ? 'opacity-20 pointer-events-none' : ''}`}>
                        <td className="py-2.5 px-2 font-mono font-bold text-[#fafafa]">{row.ticker}</td>
                        <td className="py-2.5 px-2 text-[#bcc9c8]">{row.strategy_cn}</td>
                        <td className="py-2.5 px-2 text-right font-mono text-[#fafafa]">${row.strike}</td>
                        <td className="py-2.5 px-2 text-[#bcc9c8]">
                          <span className="font-mono">{row.expiry_days}d</span>
                        </td>
                        <td className="py-2.5 px-2 text-right font-mono text-[#fafafa]">${row.premium}</td>
                        <td className="py-2.5 px-2 text-right font-mono text-[#4edea3]">{row.yield_pct}%</td>
                        <td className="py-2.5 px-2 text-right font-mono text-[#fafafa]">{row.iv_rank ?? '-'}</td>
                        <td className="py-2.5 px-2 text-right font-mono text-[#fafafa]">{row.delta?.toFixed(2) ?? '-'}</td>
                        <td className="py-2.5 px-2 text-right font-mono text-[#fafafa]">{row.prob_otm ?? '-'}%</td>
                        <td className="py-2.5 px-2 text-center">
                          <span className="inline-block px-2 py-0.5 rounded font-bold font-mono text-[11px]"
                            style={{
                              color: scoreColor(row.gbm_score),
                              backgroundColor: `${scoreColor(row.gbm_score)}15`,
                            }}>
                            {row.gbm_score}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* 免费用户限制提示 */}
              {!isPremium && results.total_matches > 5 && (
                <div className="text-center py-6 space-y-2">
                  <Lock size={20} className="mx-auto text-[#6b7280]" />
                  <p className="text-xs text-[#bcc9c8]">
                    免费版显示前 5 条 · 升级解锁全部 {results.total_matches} 条结果
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* 右侧详情面板 */}
          <div className="space-y-4">
            {selectedRow ? (
              <>
                {/* 标的信息 */}
                <div className="bg-[#1a1a1c] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-bold font-mono text-[#fafafa]">{selectedRow.ticker}</h3>
                      <p className="text-xs text-[#bcc9c8]">{selectedRow.strategy_cn}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-mono text-[#fafafa]">${selectedRow.underlying_price}</p>
                      <p className="text-[10px] text-[#6b7280]">现价</p>
                    </div>
                  </div>

                  {/* 评分 */}
                  <div className="flex items-center gap-3 p-3 bg-[#131315] rounded-lg">
                    <div className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold font-mono"
                      style={{
                        color: scoreColor(selectedRow.gbm_score),
                        border: `2px solid ${scoreColor(selectedRow.gbm_score)}`,
                      }}>
                      {selectedRow.gbm_score}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#fafafa]">GBM 综合评分</p>
                      <p className="text-xs text-[#6b7280]">
                        {selectedRow.gbm_score >= 80 ? '优秀机会' :
                         selectedRow.gbm_score >= 60 ? '良好机会' :
                         selectedRow.gbm_score >= 40 ? '一般' : '较弱'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 详细指标 */}
                <div className="bg-[#1a1a1c] rounded-xl p-4 space-y-2.5">
                  <h3 className="text-sm font-medium text-[#fafafa]">详细指标</h3>
                  <DetailRow label="行权价" value={`$${selectedRow.strike}`} />
                  <DetailRow label="到期" value={`${selectedRow.expiry} (${selectedRow.expiry_days}天)`} />
                  <DetailRow label="权利金" value={`$${selectedRow.premium}`} />
                  <DetailRow label="年化收益率" value={`${selectedRow.yield_pct}%`} highlight />
                  <DetailRow label="IV Rank" value={selectedRow.iv_rank != null ? `${selectedRow.iv_rank}%` : '-'} />
                  <DetailRow label="Delta" value={selectedRow.delta?.toFixed(3) ?? '-'} />
                  <DetailRow label="OTM 概率" value={selectedRow.prob_otm != null ? `${selectedRow.prob_otm}%` : '-'} />
                  <DetailRow label="成交量" value={selectedRow.volume?.toLocaleString()} />
                  <DetailRow label="持仓量" value={selectedRow.open_interest?.toLocaleString()} />
                  {selectedRow.spread_pct != null && (
                    <DetailRow label="买卖价差" value={`${selectedRow.spread_pct}%`}
                      warn={selectedRow.spread_pct > 5} />
                  )}
                </div>

                {/* 操作按钮 */}
                <div className="flex gap-2">
                  <button className="flex-1 py-2 rounded-lg text-xs font-medium bg-[#222224] text-[#bcc9c8]
                    hover:bg-[#2a2a2c] transition-colors flex items-center justify-center gap-1.5">
                    <BarChart3 size={14} /> 深入分析
                  </button>
                  <button className="flex-1 py-2 rounded-lg text-xs font-medium bg-[#222224] text-[#bcc9c8]
                    hover:bg-[#2a2a2c] transition-colors flex items-center justify-center gap-1.5">
                    <Activity size={14} /> 波动率
                  </button>
                </div>
              </>
            ) : (
              <div className="bg-[#1a1a1c] rounded-xl p-12 text-center space-y-3">
                <ChevronRight size={36} className="mx-auto text-[#2a2a2c]" />
                <p className="text-xs text-[#6b7280]">点击表格中的行查看详情</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 空状态 */}
      {!results && !loading && (
        <div className="bg-[#1a1a1c] rounded-xl p-12 text-center space-y-3">
          <Search size={48} className="mx-auto text-[#2a2a2c]" />
          <p className="text-[#bcc9c8] text-sm">设置筛选条件，扫描期权机会</p>
          <p className="text-[#6b7280] text-xs">支持 Covered Call、Cash Secured Put、Wheel 等策略</p>
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label, value, highlight, warn
}: {
  label: string; value: string; highlight?: boolean; warn?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1 text-xs">
      <span className="text-[#bcc9c8]">{label}</span>
      <span className={`font-mono ${warn ? 'text-[#f59e0b]' : highlight ? 'text-[#66d8d3]' : 'text-[#fafafa]'}`}>
        {value}
      </span>
    </div>
  );
}
