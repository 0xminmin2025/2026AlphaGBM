import { useTranslation } from 'react-i18next';

interface RotationStage {
  stage: string;
  description: string;
  market_breadth?: number;
}

interface RotationTimelineProps {
  currentStage?: RotationStage;
  stockStage?: string;
}

const STAGES = [
  { id: 'rotating_in', label: '轮入期', labelEn: 'Rotating In', color: 'bg-blue-500' },
  { id: 'main_rise', label: '主升期', labelEn: 'Main Rise', color: 'bg-green-500' },
  { id: 'strong_trend', label: '强趋势', labelEn: 'Strong', color: 'bg-green-600' },
  { id: 'rotating_out', label: '轮出期', labelEn: 'Rotating Out', color: 'bg-yellow-500' },
  { id: 'correction', label: '调整期', labelEn: 'Correction', color: 'bg-red-500' },
  { id: 'bottoming', label: '筑底期', labelEn: 'Bottoming', color: 'bg-orange-500' },
];

export function RotationTimeline({ currentStage, stockStage }: RotationTimelineProps) {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language?.startsWith('zh');

  const activeStageId = currentStage?.stage || stockStage || 'neutral';
  const activeIndex = STAGES.findIndex(s => s.id === activeStageId);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-medium text-gray-300">
          {t('sector.rotationStage', '轮动阶段')}
        </h4>
        {currentStage?.market_breadth !== undefined && (
          <span className="text-xs text-gray-400">
            {t('sector.marketBreadth', '市场宽度')}: {(currentStage.market_breadth * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div className="relative">
        {/* Timeline bar */}
        <div className="absolute top-3 left-0 right-0 h-1 bg-gray-700 rounded-full" />

        {/* Progress indicator */}
        <div
          className="absolute top-3 left-0 h-1 bg-primary rounded-full transition-all duration-500"
          style={{
            width: activeIndex >= 0 ? `${((activeIndex + 1) / STAGES.length) * 100}%` : '0%'
          }}
        />

        {/* Stage dots */}
        <div className="relative flex justify-between">
          {STAGES.map((stage, index) => {
            const isActive = stage.id === activeStageId;
            const isPast = activeIndex >= 0 && index <= activeIndex;

            return (
              <div key={stage.id} className="flex flex-col items-center">
                <div
                  className={`
                    w-6 h-6 rounded-full flex items-center justify-center
                    transition-all duration-300
                    ${isActive ? `${stage.color} ring-2 ring-white ring-opacity-50` : ''}
                    ${isPast && !isActive ? 'bg-primary' : ''}
                    ${!isPast && !isActive ? 'bg-gray-600' : ''}
                  `}
                >
                  {isActive && (
                    <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                  )}
                </div>
                <span
                  className={`
                    mt-2 text-xs text-center whitespace-nowrap
                    ${isActive ? 'text-primary font-medium' : 'text-gray-500'}
                  `}
                >
                  {isZh ? stage.label : stage.labelEn}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stage description */}
      {currentStage?.description && (
        <div className="mt-4 p-3 bg-gray-800 rounded-lg">
          <p className="text-sm text-gray-300">{currentStage.description}</p>
        </div>
      )}

      {/* Stage legend */}
      <div className="mt-4 flex flex-wrap gap-2">
        {STAGES.map(stage => (
          <div
            key={stage.id}
            className={`
              flex items-center gap-1 px-2 py-1 rounded text-xs
              ${stage.id === activeStageId ? 'bg-gray-700' : 'bg-transparent'}
            `}
          >
            <div className={`w-2 h-2 rounded-full ${stage.color}`} />
            <span className="text-gray-400">
              {isZh ? stage.label : stage.labelEn}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RotationTimeline;
