import { useTranslation } from 'react-i18next';

interface ConcentrationGaugeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function ConcentrationGauge({ score, size = 'md', showLabel = true }: ConcentrationGaugeProps) {
  const { t } = useTranslation();

  const sizeConfig = {
    sm: { width: 80, stroke: 8 },
    md: { width: 120, stroke: 10 },
    lg: { width: 160, stroke: 12 },
  };

  const { width, stroke } = sizeConfig[size];
  const radius = (width - stroke) / 2;
  const circumference = radius * Math.PI; // Half circle
  const progress = (score / 100) * circumference;

  const getColor = (s: number): string => {
    if (s >= 70) return '#22c55e'; // green
    if (s >= 50) return '#eab308'; // yellow
    return '#ef4444'; // red
  };

  const getLabel = (s: number): string => {
    if (s >= 70) return t('capital.high', '高');
    if (s >= 50) return t('capital.medium', '中');
    return t('capital.low', '低');
  };

  const color = getColor(score);

  return (
    <div className="flex flex-col items-center">
      <svg
        width={width}
        height={width / 2 + 20}
        className="transform"
      >
        {/* Background arc */}
        <path
          d={`M ${stroke / 2} ${width / 2} A ${radius} ${radius} 0 0 1 ${width - stroke / 2} ${width / 2}`}
          fill="none"
          stroke="#374151"
          strokeWidth={stroke}
          strokeLinecap="round"
        />

        {/* Progress arc */}
        <path
          d={`M ${stroke / 2} ${width / 2} A ${radius} ${radius} 0 0 1 ${width - stroke / 2} ${width / 2}`}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`}
          className="transition-all duration-1000 ease-out"
        />

        {/* Score text */}
        <text
          x={width / 2}
          y={width / 2 - 5}
          textAnchor="middle"
          className="fill-white text-2xl font-bold"
          style={{ fontSize: size === 'sm' ? '1.2rem' : size === 'lg' ? '2rem' : '1.5rem' }}
        >
          {score.toFixed(0)}
        </text>

        {/* Label text */}
        {showLabel && (
          <text
            x={width / 2}
            y={width / 2 + 15}
            textAnchor="middle"
            className="fill-gray-400 text-xs"
          >
            {getLabel(score)}
          </text>
        )}
      </svg>

      {/* Scale markers */}
      <div className="flex justify-between w-full px-2 text-xs text-gray-500" style={{ maxWidth: width }}>
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}

export default ConcentrationGauge;
