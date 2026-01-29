import { useTranslation } from 'react-i18next';

interface SectorAnalysis {
  sector: string;
  sector_zh?: string;
  etf_ticker?: string;
  sector_strength?: number;
  alignment_score?: number;
  correlation?: number;
  is_sector_leader?: boolean;
  outperformance_pct?: number;
  sector_rotation_premium?: number;
  sector_trend?: string;
  rotation_stage?: string;
  error?: string;
}

interface StockSectorCardProps {
  sectorAnalysis: SectorAnalysis;
  stockTicker?: string;
}

export function StockSectorCard({ sectorAnalysis, stockTicker }: StockSectorCardProps) {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language?.startsWith('zh');

  const getTrendBadge = (trend?: string) => {
    const trendConfig: Record<string, { label: string; labelZh: string; color: string }> = {
      bullish: { label: 'Bullish', labelZh: '看涨', color: 'bg-green-500' },
      rising: { label: 'Rising', labelZh: '上升', color: 'bg-green-400' },
      bearish: { label: 'Bearish', labelZh: '看跌', color: 'bg-red-500' },
      falling: { label: 'Falling', labelZh: '下降', color: 'bg-red-400' },
      neutral: { label: 'Neutral', labelZh: '中性', color: 'bg-gray-500' },
    };
    const config = trendConfig[trend || 'neutral'] || trendConfig.neutral;
    return (
      <span className={`px-2 py-0.5 rounded text-xs text-white ${config.color}`}>
        {isZh ? config.labelZh : config.label}
      </span>
    );
  };

  const getScoreBar = (score: number, label: string) => {
    const getColor = (s: number) => {
      if (s >= 70) return 'bg-green-500';
      if (s >= 50) return 'bg-yellow-500';
      return 'bg-red-500';
    };

    return (
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">{label}</span>
          <span className="text-gray-300">{score.toFixed(0)}/100</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${getColor(score)}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
    );
  };

  if (sectorAnalysis.error) {
    return (
      <div className="card p-4">
        <div className="text-center text-gray-400">
          <p>{t('sector.analysisError', '板块分析暂不可用')}</p>
          <p className="text-xs mt-1">{sectorAnalysis.error}</p>
        </div>
      </div>
    );
  }

  const sectorName = isZh ? (sectorAnalysis.sector_zh || sectorAnalysis.sector) : sectorAnalysis.sector;
  const rotationPremium = (sectorAnalysis.sector_rotation_premium || 0) * 100;

  return (
    <div className="card p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-primary">{sectorName}</h3>
          {sectorAnalysis.etf_ticker && (
            <p className="text-xs text-gray-500">ETF: {sectorAnalysis.etf_ticker}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {sectorAnalysis.is_sector_leader && (
            <span className="px-2 py-0.5 bg-yellow-500 text-black text-xs rounded font-medium">
              {t('sector.leader', '龙头')}
            </span>
          )}
          {getTrendBadge(sectorAnalysis.sector_trend)}
        </div>
      </div>

      {/* Score bars */}
      {sectorAnalysis.sector_strength !== undefined && (
        getScoreBar(sectorAnalysis.sector_strength, t('sector.sectorStrength', '板块强度'))
      )}
      {sectorAnalysis.alignment_score !== undefined && (
        getScoreBar(sectorAnalysis.alignment_score, t('sector.alignmentScore', '同步度'))
      )}

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        {/* Correlation */}
        {sectorAnalysis.correlation !== undefined && (
          <div className="bg-gray-800 rounded p-2">
            <p className="text-xs text-gray-400 mb-1">
              {t('sector.correlation', '相关性')}
            </p>
            <p className="text-lg font-semibold">
              {sectorAnalysis.correlation.toFixed(2)}
            </p>
          </div>
        )}

        {/* Rotation Premium */}
        <div className="bg-gray-800 rounded p-2">
          <p className="text-xs text-gray-400 mb-1">
            {t('sector.rotationPremium', '轮动溢价')}
          </p>
          <p className={`text-lg font-semibold ${rotationPremium >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {rotationPremium >= 0 ? '+' : ''}{rotationPremium.toFixed(2)}%
          </p>
        </div>

        {/* Outperformance */}
        {sectorAnalysis.outperformance_pct !== undefined && (
          <div className="bg-gray-800 rounded p-2">
            <p className="text-xs text-gray-400 mb-1">
              {t('sector.outperformance', '超额收益')}
            </p>
            <p className={`text-lg font-semibold ${sectorAnalysis.outperformance_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {sectorAnalysis.outperformance_pct >= 0 ? '+' : ''}{sectorAnalysis.outperformance_pct.toFixed(1)}%
            </p>
          </div>
        )}

        {/* Rotation Stage */}
        {sectorAnalysis.rotation_stage && (
          <div className="bg-gray-800 rounded p-2">
            <p className="text-xs text-gray-400 mb-1">
              {t('sector.stage', '轮动阶段')}
            </p>
            <p className="text-sm font-medium">
              {getRotationStageName(sectorAnalysis.rotation_stage, isZh)}
            </p>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="mt-4 pt-3 border-t border-gray-700">
        <p className="text-sm text-gray-300">
          {generateSummary(sectorAnalysis, stockTicker, isZh)}
        </p>
      </div>
    </div>
  );
}

function getRotationStageName(stage: string, isZh: boolean): string {
  const stages: Record<string, { zh: string; en: string }> = {
    rotating_in: { zh: '轮入期', en: 'Rotating In' },
    main_rise: { zh: '主升期', en: 'Main Rise' },
    strong_trend: { zh: '强趋势', en: 'Strong Trend' },
    rotating_out: { zh: '轮出期', en: 'Rotating Out' },
    correction: { zh: '调整期', en: 'Correction' },
    bottoming: { zh: '筑底期', en: 'Bottoming' },
    neutral: { zh: '中性', en: 'Neutral' },
  };
  const s = stages[stage] || stages.neutral;
  return isZh ? s.zh : s.en;
}

function generateSummary(analysis: SectorAnalysis, ticker?: string, isZh: boolean = true): string {
  const sectorName = isZh ? (analysis.sector_zh || analysis.sector) : analysis.sector;
  const strength = analysis.sector_strength || 50;
  const alignment = analysis.alignment_score || 50;
  const isLeader = analysis.is_sector_leader;
  const premium = (analysis.sector_rotation_premium || 0) * 100;

  if (isZh) {
    let summary = `${ticker || '该股票'}所属${sectorName}板块`;

    if (strength >= 70) {
      summary += '目前处于强势';
    } else if (strength >= 50) {
      summary += '表现中性';
    } else {
      summary += '相对较弱';
    }

    if (alignment >= 70) {
      summary += '，与板块走势高度同步';
    } else if (alignment < 40) {
      summary += '，走势与板块有所背离';
    }

    if (isLeader) {
      summary += '，是板块龙头';
    }

    if (premium > 0) {
      summary += `，建议给予+${premium.toFixed(1)}%的板块溢价`;
    } else if (premium < 0) {
      summary += `，板块因素带来${premium.toFixed(1)}%的折价`;
    }

    return summary + '。';
  } else {
    let summary = `${ticker || 'This stock'} belongs to the ${sectorName} sector`;

    if (strength >= 70) {
      summary += ' which is currently strong';
    } else if (strength >= 50) {
      summary += ' with neutral performance';
    } else {
      summary += ' which is relatively weak';
    }

    if (alignment >= 70) {
      summary += ', highly correlated with sector movement';
    } else if (alignment < 40) {
      summary += ', showing divergence from sector';
    }

    if (isLeader) {
      summary += ', acting as sector leader';
    }

    if (premium > 0) {
      summary += `. Suggests +${premium.toFixed(1)}% rotation premium`;
    } else if (premium < 0) {
      summary += `. Sector factors suggest ${premium.toFixed(1)}% discount`;
    }

    return summary + '.';
  }
}

export default StockSectorCard;
