import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import api from '@/lib/api';

interface SectorData {
  sector: string;
  sector_zh: string;
  score: number;
  change_5d: number;
  change_20d: number;
  volume_ratio: number;
  trend: string;
}

interface SectorHeatmapProps {
  market?: string;
  onSectorClick?: (sector: string) => void;
}

export function SectorHeatmap({ market = 'US', onSectorClick }: SectorHeatmapProps) {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<SectorData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get(`/api/sector/heatmap?market=${market}`);
        if (response.data.success) {
          setData(response.data.data || []);
        } else {
          setError(response.data.error || 'Failed to fetch data');
        }
      } catch (err: any) {
        setError(err.message || 'Network error');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [market]);

  const getScoreColor = (score: number): string => {
    if (score >= 70) return 'bg-green-600';
    if (score >= 60) return 'bg-green-500';
    if (score >= 50) return 'bg-yellow-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getChangeColor = (change: number): string => {
    if (change > 3) return 'text-green-400';
    if (change > 0) return 'text-green-300';
    if (change < -3) return 'text-red-400';
    if (change < 0) return 'text-red-300';
    return 'text-gray-400';
  };

  const getTrendIcon = (trend: string): string => {
    switch (trend) {
      case 'bullish':
      case 'rising':
        return '↑';
      case 'bearish':
      case 'falling':
        return '↓';
      default:
        return '→';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-400 py-8">
        <p>{error}</p>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="text-center text-gray-400 py-8">
        <p>{t('sector.noData', 'No sector data available')}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {data.map((sector) => (
        <div
          key={sector.sector}
          className="card p-3 cursor-pointer transition-all hover:scale-105"
          onClick={() => onSectorClick?.(sector.sector)}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-sm truncate">
              {i18n.language?.startsWith('zh') ? sector.sector_zh : sector.sector}
            </span>
            <span className="text-lg">{getTrendIcon(sector.trend)}</span>
          </div>

          <div className="flex items-center gap-2 mb-2">
            <div
              className={`w-full h-2 rounded-full ${getScoreColor(sector.score)} opacity-80`}
              style={{ width: `${sector.score}%` }}
            />
            <span className="text-xs text-gray-400 whitespace-nowrap">
              {sector.score.toFixed(0)}
            </span>
          </div>

          <div className="flex justify-between text-xs">
            <span className={getChangeColor(sector.change_5d)}>
              5D: {sector.change_5d > 0 ? '+' : ''}{sector.change_5d.toFixed(1)}%
            </span>
            <span className={getChangeColor(sector.change_20d)}>
              20D: {sector.change_20d > 0 ? '+' : ''}{sector.change_20d.toFixed(1)}%
            </span>
          </div>

          {sector.volume_ratio > 1.5 && (
            <div className="mt-1 text-xs text-yellow-400">
              {t('sector.volumeHigh', 'Volume +')}
              {((sector.volume_ratio - 1) * 100).toFixed(0)}%
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default SectorHeatmap;
