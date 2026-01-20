/**
 * 叙事雷达组件 - Narrative Radar Component
 * AI 驱动的概念/叙事股票发现功能
 */

import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import api from '@/lib/api';

interface OptionsStrategy {
  zebra?: {
    available: boolean;
    description: string;
    leverage: string;
    theta_cost: string;
  };
  leaps?: {
    available: boolean;
    description: string;
    leverage: string;
    theta_cost: string;
  };
}

interface NarrativeStock {
  symbol: string;
  name: string;
  relevance_score: number;
  reason: string;
  position_change?: string;
  options_strategy?: OptionsStrategy;
}

interface NarrativeInfo {
  name: string;
  type: string;
  thesis?: string;
  risk_factors?: string[];
}

interface NarrativeResult {
  narrative: NarrativeInfo;
  stocks: NarrativeStock[];
  summary?: string;
  error?: string;
}

interface PresetNarrative {
  key: string;
  name_zh: string;
  name_en: string;
  type: string;
  description_zh: string;
  description_en: string;
}

interface GroupedPresets {
  person: PresetNarrative[];
  institution: PresetNarrative[];
  theme: PresetNarrative[];
}

const PRESET_ICONS: Record<string, string> = {
  musk: 'bi-rocket-takeoff',
  buffett: 'bi-briefcase',
  ark: 'bi-graph-up-arrow',
  dalio: 'bi-globe',
  burry: 'bi-shield-exclamation',
  ai_chips: 'bi-cpu',
  glp1: 'bi-capsule',
  quantum: 'bi-atom',
  robotics: 'bi-robot',
  ev_battery: 'bi-battery-charging'
};

interface NarrativeRadarProps {
  /** 当用户选择股票进行详细分析时的回调 */
  onSelectStock?: (symbol: string) => void;
  /** 是否隐藏标题（嵌入模式时使用） */
  hideTitle?: boolean;
}

export function NarrativeRadar({ onSelectStock, hideTitle = false }: NarrativeRadarProps) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  const [concept, setConcept] = useState('');
  const [market, setMarket] = useState('US');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NarrativeResult | null>(null);
  const [presets, setPresets] = useState<GroupedPresets | null>(null);
  const [expandedStock, setExpandedStock] = useState<string | null>(null);
  // 保存当前叙事key用于语言切换时重新请求
  const currentNarrativeKeyRef = useRef<string | null>(null);
  const prevLangRef = useRef(isZh);
  const marketRef = useRef(market);
  const hasResultRef = useRef(false);

  // 同步 refs
  marketRef.current = market;
  hasResultRef.current = !!result;

  // 加载预设叙事
  useEffect(() => {
    api.get('/narrative/presets')
      .then(res => setPresets(res.data))
      .catch(console.error);
  }, []);

  // 语言切换时，如果已有结果，重新请求以获取对应语言的数据
  useEffect(() => {
    // 只有当语言真正发生变化时才刷新
    if (prevLangRef.current !== isZh) {
      prevLangRef.current = isZh;

      // 如果有当前叙事key且有结果，重新请求
      if (currentNarrativeKeyRef.current && hasResultRef.current) {
        const refreshData = async () => {
          setLoading(true);
          try {
            const response = await api.post('/narrative/analyze', {
              concept: '',
              narrative_key: currentNarrativeKeyRef.current,
              market: marketRef.current,
              lang: isZh ? 'zh' : 'en'
            });
            setResult(response.data);
          } catch (error) {
            console.error('Failed to refresh narrative data:', error);
          } finally {
            setLoading(false);
          }
        };
        refreshData();
      }
    }
  }, [isZh]); // 只依赖 isZh，避免其他依赖导致不必要的触发

  const handleAnalyze = async (narrativeKey?: string) => {
    if (!concept.trim() && !narrativeKey) return;

    setLoading(true);
    setResult(null);
    // 保存当前的 narrativeKey 用于语言切换时刷新
    currentNarrativeKeyRef.current = narrativeKey || null;

    try {
      const response = await api.post('/narrative/analyze', {
        concept: narrativeKey ? '' : concept.trim(),
        narrative_key: narrativeKey,
        market,
        lang: isZh ? 'zh' : 'en'  // 传递当前语言
      });
      setResult(response.data);
    } catch (error) {
      setResult({
        narrative: { name: concept, type: 'custom' },
        error: 'Failed to analyze',
        stocks: []
      });
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-slate-400';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-slate-500';
  };

  const renderPresetButton = (preset: PresetNarrative) => (
    <button
      key={preset.key}
      onClick={() => handleAnalyze(preset.key)}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1c1c1e] hover:bg-[#27272a]
                 rounded-full transition-all border border-[#3f3f46] hover:border-[#0D9B97]/50
                 disabled:opacity-50 text-sm"
    >
      <i className={`bi ${PRESET_ICONS[preset.key] || 'bi-tag'} text-[#0D9B97]`}></i>
      <span className="text-white">
        {isZh ? preset.name_zh : preset.name_en}
      </span>
    </button>
  );

  return (
    <div className={hideTitle ? '' : 'card p-6'}>
      {/* 标题 - 可隐藏 */}
      {!hideTitle && (
        <div className="flex items-center gap-2 mb-6">
          <i className="bi bi-broadcast text-[#0D9B97] text-xl"></i>
          <h3 className="text-white text-lg font-semibold">
            {isZh ? '叙事雷达' : 'Narrative Radar'}
          </h3>
          <span className="text-slate-500 text-sm ml-2">
            {isZh ? '发现投资叙事，获取跟单信号' : 'Discover narratives, get trading signals'}
          </span>
        </div>
      )}

      {/* 搜索栏 */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          placeholder={isZh
            ? '输入自定义概念，或选择下方热门叙事...'
            : 'Enter custom concept, or select popular narratives below...'}
          className="flex-1 bg-[#27272a] border border-[#3f3f46] rounded-lg px-4 py-3
                     text-white placeholder-slate-500 focus:border-[#0D9B97] focus:outline-none"
          onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
        />
        <select
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          className="bg-[#27272a] border border-[#3f3f46] rounded-lg px-4 py-3 text-white"
        >
          <option value="US">{isZh ? '美股' : 'US'}</option>
          <option value="HK">{isZh ? '港股' : 'HK'}</option>
          <option value="CN">{isZh ? 'A股' : 'CN'}</option>
        </select>
        <button
          onClick={() => handleAnalyze()}
          disabled={loading || !concept.trim()}
          className="px-6 py-3 bg-[#0D9B97] hover:bg-[#0D9B97]/80 disabled:bg-slate-600
                     text-white rounded-lg transition-all flex items-center gap-2"
        >
          {loading ? (
            <i className="bi bi-arrow-repeat animate-spin"></i>
          ) : (
            <i className="bi bi-search"></i>
          )}
          {isZh ? '搜索' : 'Search'}
        </button>
      </div>

      {/* 预设叙事 - 仅在无结果时显示 */}
      {!result && !loading && presets && (
        <div className="space-y-4">
          {/* 人物/机构叙事 */}
          <div>
            <h4 className="text-slate-500 text-xs mb-2 flex items-center gap-1">
              <i className="bi bi-person-circle"></i>
              {isZh ? '人物 & 机构' : 'People & Institutions'}
            </h4>
            <div className="flex flex-wrap gap-2">
              {presets.person.map(renderPresetButton)}
              {presets.institution.map(renderPresetButton)}
            </div>
          </div>

          {/* 主题叙事 */}
          <div>
            <h4 className="text-slate-500 text-xs mb-2 flex items-center gap-1">
              <i className="bi bi-tag"></i>
              {isZh ? '主题概念' : 'Themes'}
            </h4>
            <div className="flex flex-wrap gap-2">
              {presets.theme.map(renderPresetButton)}
            </div>
          </div>
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-12">
          <i className="bi bi-broadcast text-[#0D9B97] text-4xl animate-pulse mb-4"></i>
          <div className="text-slate-400">
            {isZh ? '正在扫描叙事信号...' : 'Scanning narrative signals...'}
          </div>
        </div>
      )}

      {/* 结果展示 */}
      {result && !result.error && !loading && (
        <div className="space-y-4">
          {/* 叙事信息卡片 */}
          <div className="p-4 bg-[#0D9B97]/10 border border-[#0D9B97]/30 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[#0D9B97] font-semibold text-lg">
                {result.narrative.name}
              </div>
              <button
                onClick={() => setResult(null)}
                className="text-slate-400 hover:text-white"
              >
                <i className="bi bi-x-lg"></i>
              </button>
            </div>
            {result.narrative.thesis && (
              <div className="text-slate-300 text-sm mb-2">
                {result.narrative.thesis}
              </div>
            )}
            {result.narrative.risk_factors && result.narrative.risk_factors.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {result.narrative.risk_factors.map((risk, idx) => (
                  <span key={idx} className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded">
                    <i className="bi bi-exclamation-triangle mr-1"></i>
                    {risk}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 股票列表 */}
          <div className="space-y-3">
            {result.stocks.map((stock, idx) => (
              <div
                key={stock.symbol}
                className="bg-[#1c1c1e] rounded-lg overflow-hidden"
              >
                {/* 股票主信息 */}
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer hover:bg-[#27272a] transition-all"
                  onClick={() => setExpandedStock(
                    expandedStock === stock.symbol ? null : stock.symbol
                  )}
                >
                  <span className="text-slate-500 font-mono w-6">#{idx + 1}</span>

                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold">{stock.symbol}</span>
                      <span className="text-slate-400 text-sm">{stock.name}</span>
                      {stock.position_change && stock.position_change !== '持平' && stock.position_change !== 'Hold' && stock.position_change !== '' && (
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          stock.position_change === '增持' || stock.position_change === '新建仓' ||
                          stock.position_change === 'Added' || stock.position_change === 'New'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {stock.position_change}
                        </span>
                      )}
                    </div>
                    <div className="text-slate-500 text-xs mt-1">{stock.reason}</div>
                  </div>

                  {/* 相关度 */}
                  <div className="text-right mr-4">
                    <div className={`text-lg font-bold ${getScoreColor(stock.relevance_score)}`}>
                      {stock.relevance_score}%
                    </div>
                    <div className="w-20 h-1.5 bg-[#27272a] rounded-full overflow-hidden mt-1">
                      <div
                        className={`h-full ${getScoreBarColor(stock.relevance_score)} rounded-full`}
                        style={{ width: `${stock.relevance_score}%` }}
                      />
                    </div>
                  </div>

                  {/* 展开箭头 */}
                  <i className={`bi ${expandedStock === stock.symbol ? 'bi-chevron-up' : 'bi-chevron-down'} text-slate-400`}></i>
                </div>

                {/* 期权策略详情（展开） */}
                {expandedStock === stock.symbol && stock.options_strategy && (
                  <div className="px-4 pb-4 border-t border-[#27272a]">
                    <div className="pt-4">
                      <div className="text-slate-400 text-sm mb-3 flex items-center gap-2">
                        <i className="bi bi-lightning-charge text-[#0D9B97]"></i>
                        {isZh ? '期权杠杆策略' : 'Options Leverage Strategies'}
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {/* ZEBRA 策略 */}
                        {stock.options_strategy.zebra?.available && (
                          <div className="p-3 bg-[#27272a] rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-white font-medium">ZEBRA</span>
                              <span className="text-[#0D9B97] font-bold">
                                {stock.options_strategy.zebra.leverage}
                              </span>
                            </div>
                            <div className="text-slate-400 text-xs mb-2">
                              {stock.options_strategy.zebra.description}
                            </div>
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-slate-500">Theta:</span>
                              <span className="text-green-400">
                                {stock.options_strategy.zebra.theta_cost}
                              </span>
                            </div>
                          </div>
                        )}

                        {/* LEAPS 策略 */}
                        {stock.options_strategy.leaps?.available && (
                          <div className="p-3 bg-[#27272a] rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-white font-medium">LEAPS</span>
                              <span className="text-[#0D9B97] font-bold">
                                {stock.options_strategy.leaps.leverage}
                              </span>
                            </div>
                            <div className="text-slate-400 text-xs mb-2">
                              {stock.options_strategy.leaps.description}
                            </div>
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-slate-500">Theta:</span>
                              <span className="text-yellow-400">
                                {stock.options_strategy.leaps.theta_cost}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 跳转分析按钮 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onSelectStock) {
                            // 使用回调，不刷新页面
                            onSelectStock(stock.symbol);
                          } else {
                            // 兼容旧版：URL 跳转
                            window.location.href = `/?symbol=${stock.symbol}`;
                          }
                        }}
                        className="mt-3 w-full py-2 bg-[#0D9B97]/20 hover:bg-[#0D9B97]/30
                                   text-[#0D9B97] rounded-lg transition-all flex items-center justify-center gap-2"
                      >
                        <i className="bi bi-graph-up"></i>
                        {isZh ? '查看详细分析' : 'View Detailed Analysis'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* 总结 */}
          {result.summary && (
            <div className="p-4 bg-[#27272a] rounded-lg">
              <div className="flex items-start gap-2">
                <i className="bi bi-lightbulb text-yellow-400 mt-0.5"></i>
                <div className="text-slate-300 text-sm">{result.summary}</div>
              </div>
            </div>
          )}

          {/* 风险提示 */}
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <i className="bi bi-exclamation-triangle"></i>
              {isZh
                ? '风险提示：期权策略涉及杠杆，最大亏损可达100%本金。以上分析基于AI生成，仅供参考。'
                : 'Risk Warning: Options strategies involve leverage. Maximum loss can be 100% of principal. Analysis is AI-generated for reference only.'}
            </div>
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {result?.error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="text-red-400">{result.error}</div>
        </div>
      )}
    </div>
  );
}
