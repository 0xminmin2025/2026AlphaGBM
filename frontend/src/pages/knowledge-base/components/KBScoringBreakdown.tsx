import { useTranslation } from 'react-i18next';

interface ScoringFactor {
  name: string;
  nameEn: string;
  weight: number;
  score: number;
  description: string;
}

const factors: ScoringFactor[] = [
  { name: '期权费收入', nameEn: 'Premium Income', weight: 20, score: 85, description: '年化收益率计算，越高越好' },
  { name: '趋势匹配', nameEn: 'Trend Match', weight: 15, score: 72, description: '支撑位接近度与板块动量' },
  { name: '支撑强度', nameEn: 'Support Strength', weight: 15, score: 80, description: '技术支撑识别与历史反弹模式' },
  { name: 'ATR安全距离', nameEn: 'ATR Safety', weight: 15, score: 75, description: '波动率调整的安全缓冲垫' },
  { name: '流动性', nameEn: 'Liquidity', weight: 15, score: 90, description: '买卖价差与成交量/持仓量' },
  { name: '时间价值', nameEn: 'Time Value', weight: 10, score: 68, description: 'Theta衰减优化与到期时间选择' },
  { name: 'IV排名', nameEn: 'IV Rank', weight: 10, score: 65, description: '隐含波动率百分位——权利金丰厚程度' },
];

export default function KBScoringBreakdown() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  const totalScore = Math.round(
    factors.reduce((sum, f) => sum + (f.score * f.weight) / 100, 0)
  );

  return (
    <div className="my-8 rounded-xl border border-white/10 bg-[#18181B] overflow-hidden">
      {/* Header with total score */}
      <div className="px-5 py-5 border-b border-white/10 flex items-center justify-between">
        <div>
          <h4 className="text-base font-semibold text-[#FAFAFA]">
            {isZh ? 'AlphaGBM Sell Put 评分模型' : 'AlphaGBM Sell Put Scoring Model'}
          </h4>
          <p className="text-sm text-[#71717A] mt-1">
            {isZh ? '7大维度综合评估期权机会质量' : '7 dimensions to evaluate option opportunity quality'}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="flex items-baseline gap-0.5">
            <span className="text-3xl font-bold font-mono text-[#10B981]">{totalScore}</span>
            <span className="text-sm text-[#71717A]">/ 100</span>
          </div>
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="px-5 pt-3 pb-2">
        <div className="w-full h-2 bg-[#27272A] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#0D9B97] to-[#10B981] transition-all duration-500"
            style={{ width: `${totalScore}%` }}
          />
        </div>
      </div>

      {/* Factor breakdown */}
      <div className="px-5 pb-5 space-y-4 mt-2">
        {factors.map((f) => (
          <div key={f.name}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-medium text-[#FAFAFA]">
                {isZh ? f.name : f.nameEn}
              </span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-[#71717A]">
                  {isZh ? `权重: ${f.weight}%` : `Weight: ${f.weight}%`}
                </span>
                <span className="text-sm font-mono font-medium text-[#0D9B97] w-8 text-right">
                  {f.score}
                </span>
              </div>
            </div>
            <div className="w-full h-1.5 bg-[#27272A] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${f.score}%`,
                  backgroundColor: f.score >= 80 ? '#10B981' : f.score >= 60 ? '#0D9B97' : '#F59E0B',
                }}
              />
            </div>
            <p className="text-xs text-[#71717A] mt-1">{isZh ? f.description : f.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
