import { useTranslation } from 'react-i18next';

interface StageInfo {
  name: string;
  name_en?: string;
  description: string;
  capital_factor: number;
  probability_persistence?: number;
}

interface PropagationStageProps {
  stage: string;
  stageInfo?: StageInfo;
  signals?: string[];
  showDetails?: boolean;
}

const STAGE_CONFIG: Record<string, { color: string; icon: string; order: number }> = {
  leader_start: { color: 'bg-blue-500', icon: '🚀', order: 1 },
  early_spread: { color: 'bg-green-400', icon: '📈', order: 2 },
  full_spread: { color: 'bg-green-500', icon: '🔥', order: 3 },
  high_divergence: { color: 'bg-yellow-500', icon: '⚠️', order: 4 },
  retreat: { color: 'bg-red-500', icon: '📉', order: 5 },
  neutral: { color: 'bg-gray-500', icon: '➖', order: 0 },
};

const ALL_STAGES = [
  { id: 'leader_start', name: '龙头启动', nameEn: 'Leader Start' },
  { id: 'early_spread', name: '扩散初期', nameEn: 'Early Spread' },
  { id: 'full_spread', name: '全面扩散', nameEn: 'Full Spread' },
  { id: 'high_divergence', name: '高位分化', nameEn: 'Divergence' },
  { id: 'retreat', name: '退潮期', nameEn: 'Retreat' },
];

export function PropagationStage({
  stage,
  stageInfo,
  signals = [],
  showDetails = true,
}: PropagationStageProps) {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language?.startsWith('zh');

  const config = STAGE_CONFIG[stage] || STAGE_CONFIG.neutral;
  const currentIndex = ALL_STAGES.findIndex(s => s.id === stage);

  const stageName = stageInfo
    ? (isZh ? stageInfo.name : stageInfo.name_en || stageInfo.name)
    : (isZh ? '中性期' : 'Neutral');

  const capitalFactor = stageInfo?.capital_factor || 0;
  const persistence = stageInfo?.probability_persistence || 0.5;

  return (
    <div className="space-y-4">
      {/* Current stage indicator */}
      <div className="flex items-center gap-3">
        <div className={`w-12 h-12 rounded-full ${config.color} flex items-center justify-center text-xl`}>
          {config.icon}
        </div>
        <div>
          <h4 className="text-lg font-semibold text-white">{stageName}</h4>
          {stageInfo?.description && (
            <p className="text-sm text-gray-400">{stageInfo.description}</p>
          )}
        </div>
      </div>

      {/* Stage progress bar */}
      <div className="relative">
        <div className="flex justify-between mb-2">
          {ALL_STAGES.map((s, idx) => {
            const isActive = s.id === stage;
            const isPast = currentIndex >= 0 && idx < currentIndex;
            const stageConf = STAGE_CONFIG[s.id];

            return (
              <div key={s.id} className="flex flex-col items-center flex-1">
                <div
                  className={`
                    w-4 h-4 rounded-full mb-1 transition-all
                    ${isActive ? stageConf.color + ' ring-2 ring-white' : ''}
                    ${isPast ? 'bg-gray-500' : ''}
                    ${!isPast && !isActive ? 'bg-gray-700' : ''}
                  `}
                />
                <span className={`text-xs text-center ${isActive ? 'text-white' : 'text-gray-500'}`}>
                  {isZh ? s.name : s.nameEn}
                </span>
              </div>
            );
          })}
        </div>

        {/* Connection lines */}
        <div className="absolute top-2 left-4 right-4 h-0.5 bg-gray-700 -z-10" />
        {currentIndex >= 0 && (
          <div
            className="absolute top-2 left-4 h-0.5 bg-primary -z-10 transition-all duration-500"
            style={{ width: `${(currentIndex / (ALL_STAGES.length - 1)) * 100}%` }}
          />
        )}
      </div>

      {showDetails && (
        <>
          {/* Capital factor and persistence */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-1">
                {t('capital.factor', '资金因子')}
              </p>
              <p className={`text-xl font-bold ${capitalFactor >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {capitalFactor >= 0 ? '+' : ''}{(capitalFactor * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-1">
                {t('capital.persistence', '持续概率')}
              </p>
              <p className="text-xl font-bold text-white">
                {(persistence * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Signals */}
          {signals.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-2">
                {t('capital.signals', '资金信号')}
              </p>
              <div className="flex flex-wrap gap-2">
                {signals.map((signal, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-gray-700 rounded text-xs text-gray-300"
                  >
                    {signal}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default PropagationStage;
