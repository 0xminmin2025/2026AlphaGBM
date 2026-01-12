import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

// Now each history item contains the complete analysis data
interface CompleteAnalysisData {
  success: boolean;
  data: any;  // Complete market data
  risk: any;  // Complete risk data
  report: string;  // AI analysis report
  history_metadata: {
    id: number;
    created_at: string;
    is_from_history: boolean;
    ticker: string;
    style: string;
    incomplete_data?: boolean;
  };
}

interface StockAnalysisHistoryProps {
  onSelectHistory?: (ticker: string, style: string) => void;  // Simplified to pass ticker/style
  onViewFullReport?: (analysisData: CompleteAnalysisData) => void;  // Pass complete analysis data
  tickerFilter?: string;
}

const StockAnalysisHistory: React.FC<StockAnalysisHistoryProps> = ({
  onSelectHistory,
  onViewFullReport,
  tickerFilter
}) => {
  const [history, setHistory] = useState<CompleteAnalysisData[]>([]);  // Now stores complete data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [searchTicker, setSearchTicker] = useState(tickerFilter || '');
  const [selectedDetail, setSelectedDetail] = useState<any>(null);
  const [showDetail, setShowDetail] = useState(false);

  const loadHistory = async (pageNum: number = 1, reset: boolean = false) => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: pageNum.toString(),
        per_page: '10'
      });

      if (searchTicker) {
        params.append('ticker', searchTicker.toUpperCase());
      }

      const response = await api.get(`/stock/history?${params}`);

      if (response.data.success) {
        // Backend now returns complete analysis data for each item
        const newItems = response.data.data.items;
        console.log('Loaded complete analysis history:', newItems.length, 'items');

        setHistory(reset ? newItems : [...history, ...newItems]);
        setHasMore(response.data.data.pagination.has_next);
      } else {
        setError(response.data.error || 'Failed to load history');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  // Extract display info from complete analysis data
  const extractDisplayInfo = (analysisData: CompleteAnalysisData) => {
    const metadata = analysisData.history_metadata;
    const data = analysisData.data || {};
    const risk = analysisData.risk || {};

    return {
      id: metadata.id,
      ticker: metadata.ticker,
      style: metadata.style,
      current_price: data.price || null,
      target_price: data.target_price || null,
      stop_loss_price: data.stop_loss_price || null,
      market_sentiment: data.market_sentiment || null,
      risk_score: risk.score || null,
      risk_level: risk.level || null,
      position_size: risk.suggested_position || null,
      ai_summary: analysisData.report ? analysisData.report.substring(0, 200) + '...' : null,
      created_at: metadata.created_at
    };
  };

  // Load full report directly from memory (no network request)
  const loadFullReport = (analysisData: CompleteAnalysisData) => {
    if (onViewFullReport) {
      console.log('Loading complete historical analysis from memory:', analysisData);
      // Pass the complete analysis data directly to parent
      onViewFullReport(analysisData);
    }
  };

  const handleSearch = () => {
    setPage(1);
    setHistory([]);
    setHasMore(true);
    loadHistory(1, true);
  };

  const getRiskClass = (riskLevel: string | null): string => {
    switch (riskLevel?.toLowerCase()) {
      case 'low': return 'risk-low';
      case 'medium': return 'risk-med';
      case 'high': return 'risk-high';
      default: return 'text-muted';
    }
  };

  const getRecommendationClass = (action: string | null): string => {
    switch (action?.toLowerCase()) {
      case 'buy': return 'text-success';
      case 'sell': return 'text-danger';
      case 'hold': return 'text-warning';
      default: return 'text-muted';
    }
  };

  const formatCurrency = (value: number | null): string => {
    if (value === null || value === undefined) return 'N/A';
    return `$${value.toFixed(2)}`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  useEffect(() => {
    loadHistory(1, true);
  }, []);

  useEffect(() => {
    if (tickerFilter !== searchTicker) {
      setSearchTicker(tickerFilter || '');
    }
  }, [tickerFilter]);

  if (loading && history.length === 0) {
    return (
      <div className="card shadow-lg" style={{ padding: '2rem' }}>
        <div className="text-center">
          <div className="spinner" style={{ margin: '0 auto 1rem' }}></div>
          <p style={{ color: 'var(--muted-foreground)' }}>加载分析历史中...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="card shadow-lg mb-4" style={{ padding: '1.5rem' }}>
        <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.3rem', fontWeight: 600 }}>
          <i className="bi bi-clock-history"></i>
          分析历史
        </h5>

        {/* Search */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4 mb-4">
          <input
            type="text"
            className="form-control"
            placeholder="搜索股票代码..."
            value={searchTicker}
            onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            style={{
              background: 'var(--muted)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '0.75rem',
              color: 'var(--foreground)'
            }}
          />
          <Button
            onClick={handleSearch}
            className="btn-primary"
            style={{
              background: 'var(--primary)',
              border: '1px solid var(--primary)',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '8px',
              fontWeight: 500
            }}
          >
            <i className="bi bi-search mr-2"></i>
            搜索
          </Button>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--bear)', color: 'var(--bear)' }}>
            {error}
          </div>
        )}

        {history.length === 0 && !loading ? (
          <div className="text-center py-20 text-muted">
            <i className="bi bi-inbox text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
            <p>暂无分析历史记录</p>
          </div>
        ) : (
          <div style={{ maxHeight: '600px', overflow: 'auto' }}>
            {history.map((analysisData) => {
              const item = extractDisplayInfo(analysisData);  // Extract display info from complete data

              return (
                <div
                  key={item.id}
                  className="card mb-3"
                  style={{
                    padding: '1.5rem',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease'
                  }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                        {item.ticker}
                      </span>
                      <span className="badge-primary">{item.style}</span>
                      {item.risk_level && (
                        <span className={`badge-primary ${getRiskClass(item.risk_level)}`}>
                          {item.risk_level}
                        </span>
                      )}
                      <span className="badge-primary" style={{ background: 'rgba(13, 155, 151, 0.2)' }}>
                        <i className="bi bi-clock-history mr-1"></i>
                        历史分析
                      </span>
                    </div>
                    <span className="text-muted" style={{ fontSize: '0.9rem' }}>
                      {formatDate(item.created_at)}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                    <div>
                      <div className="metric-label">当前价格</div>
                      <div className="metric-value" style={{ fontSize: '1.1rem', color: 'var(--foreground)' }}>
                        {formatCurrency(item.current_price)}
                      </div>
                    </div>
                    <div>
                      <div className="metric-label">目标价格</div>
                      <div className="metric-value" style={{ fontSize: '1.1rem', color: 'var(--bull)' }}>
                        {formatCurrency(item.target_price)}
                      </div>
                    </div>
                    <div>
                      <div className="metric-label">风险评分</div>
                      <div className={`metric-value ${getRiskClass(item.risk_level)}`} style={{ fontSize: '1.1rem' }}>
                        {item.risk_score}/10
                      </div>
                    </div>
                    <div>
                      <div className="metric-label">建议仓位</div>
                      <div className="metric-value" style={{ fontSize: '1.1rem', color: 'var(--primary)' }}>
                        {item.position_size}%
                      </div>
                    </div>
                  </div>

                  {item.ai_summary && (
                    <div className="text-muted" style={{
                      fontSize: '0.9rem',
                      lineHeight: 1.5,
                      maxHeight: '3rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical'
                    }}>
                      {item.ai_summary}
                    </div>
                  )}

                  <div className="flex gap-2 mt-3">
                    {onViewFullReport && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          loadFullReport(analysisData);  // Pass complete data directly
                        }}
                        style={{
                          background: 'var(--primary)',
                          border: '1px solid var(--primary)',
                          color: 'white',
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          fontSize: '0.85rem'
                        }}
                      >
                        <i className="bi bi-file-earmark-text mr-1"></i>
                        查看完整报告
                      </Button>
                    )}
                    {onSelectHistory && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectHistory(item.ticker, item.style);  // Pass ticker and style
                        }}
                        style={{
                          background: 'var(--muted)',
                          border: '1px solid var(--border)',
                          color: 'var(--foreground)',
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          fontSize: '0.85rem'
                        }}
                      >
                        <i className="bi bi-arrow-repeat mr-1"></i>
                        重新分析
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}

            {hasMore && (
              <div className="text-center pt-4">
                <Button
                  onClick={() => {
                    const nextPage = page + 1;
                    setPage(nextPage);
                    loadHistory(nextPage);
                  }}
                  disabled={loading}
                  style={{
                    background: 'var(--muted)',
                    border: '1px solid var(--border)',
                    color: 'var(--foreground)',
                    padding: '0.75rem 2rem',
                    borderRadius: '8px'
                  }}
                >
                  {loading ? (
                    <>
                      <div className="spinner" style={{ width: '16px', height: '16px', marginRight: '0.5rem' }}></div>
                      加载中...
                    </>
                  ) : (
                    '加载更多'
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {showDetail && selectedDetail && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setShowDetail(false)}
        >
          <div
            className="card shadow-lg"
            style={{
              width: '90vw',
              maxWidth: '800px',
              maxHeight: '80vh',
              overflow: 'auto',
              padding: '2rem',
              margin: '2rem'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h4 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--primary)' }}>
                {selectedDetail.ticker} 分析详情
              </h4>
              <button
                onClick={() => setShowDetail(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--muted-foreground)',
                  fontSize: '1.5rem',
                  cursor: 'pointer'
                }}
              >
                <i className="bi bi-x"></i>
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
              <div>
                <div className="metric-label">当前价格</div>
                <div className="metric-value" style={{ color: 'var(--foreground)' }}>
                  {formatCurrency(selectedDetail.current_price)}
                </div>
              </div>
              <div>
                <div className="metric-label">目标价格</div>
                <div className="metric-value" style={{ color: 'var(--bull)' }}>
                  {formatCurrency(selectedDetail.target_price)}
                </div>
              </div>
              <div>
                <div className="metric-label">止损价格</div>
                <div className="metric-value" style={{ color: 'var(--bear)' }}>
                  {formatCurrency(selectedDetail.stop_loss_price)}
                </div>
              </div>
              <div>
                <div className="metric-label">市场情绪</div>
                <div className="metric-value" style={{ color: 'var(--foreground)' }}>
                  {selectedDetail.market_sentiment?.toFixed(1) || 'N/A'}
                </div>
              </div>
              <div>
                <div className="metric-label">风险评分</div>
                <div className={`metric-value ${getRiskClass(selectedDetail.risk_level)}`}>
                  {selectedDetail.risk_score?.toFixed(1) || 'N/A'}
                </div>
              </div>
              <div>
                <div className="metric-label">EV评分</div>
                <div className="metric-value" style={{ color: 'var(--primary)' }}>
                  {selectedDetail.ev_weighted_pct?.toFixed(1) || 'N/A'}%
                </div>
              </div>
            </div>

            {selectedDetail.ai_summary && (
              <div>
                <h5 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: 'var(--foreground)' }}>
                  AI分析摘要
                </h5>
                <div
                  style={{
                    background: 'var(--muted)',
                    padding: '1rem',
                    borderRadius: '8px',
                    color: 'var(--muted-foreground)',
                    lineHeight: 1.6
                  }}
                >
                  {selectedDetail.ai_summary}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default StockAnalysisHistory;