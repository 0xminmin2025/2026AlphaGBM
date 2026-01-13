import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
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
  const [allHistory, setAllHistory] = useState<CompleteAnalysisData[]>([]);  // Cache all loaded data
  const [filteredHistory, setFilteredHistory] = useState<CompleteAnalysisData[]>([]);  // Filtered data for display
  const [loading, setLoading] = useState(false);  // Start as false, load on demand
  const [error, setError] = useState<string | null>(null);
  const [isDataLoaded, setIsDataLoaded] = useState(false);  // Track if data has been loaded
  const [searchTicker, setSearchTicker] = useState(tickerFilter || '');

  // Load all historical data (only when user explicitly requests or first time)
  const loadAllHistory = async (forceRefresh: boolean = false) => {
    if (isDataLoaded && !forceRefresh) {
      console.log('History already loaded, skipping network request');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Load a large amount of data to minimize requests (get more at once)
      const allData: CompleteAnalysisData[] = [];
      let currentPage = 1;
      let hasMoreData = true;

      while (hasMoreData && currentPage <= 10) { // Limit to prevent infinite loading
        const params = new URLSearchParams({
          page: currentPage.toString(),
          per_page: '50'  // Get 50 items per page for efficient loading
        });

        const response = await api.get(`/stock/history?${params}`);

        if (response.data.success) {
          const newItems = response.data.data.items;
          allData.push(...newItems);
          hasMoreData = response.data.data.pagination.has_next;
          currentPage++;

          console.log(`Loaded page ${currentPage - 1}, items: ${newItems.length}, total: ${allData.length}`);
        } else {
          throw new Error(response.data.error || 'Failed to load history');
        }
      }

      setAllHistory(allData);
      setIsDataLoaded(true);
      console.log(`Completed loading history: ${allData.length} total items`);

      // Apply current search filter
      performLocalSearch(allData, searchTicker);

    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  // Perform local search on cached data (real-time, no network request)
  const performLocalSearch = (dataToSearch: CompleteAnalysisData[], searchQuery: string) => {
    if (!searchQuery.trim()) {
      setFilteredHistory(dataToSearch);
      return;
    }

    const query = searchQuery.toUpperCase().trim();
    const filtered = dataToSearch.filter(analysisData => {
      const ticker = analysisData.history_metadata?.ticker || '';
      return ticker.toUpperCase().includes(query);
    });

    setFilteredHistory(filtered);
    console.log(`Local search for "${searchQuery}": ${filtered.length} results found`);
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

  // Handle real-time search input changes
  const handleSearchChange = (newSearchValue: string) => {
    setSearchTicker(newSearchValue);
    // Perform local search immediately on cached data
    performLocalSearch(allHistory, newSearchValue);
  };

  // Manual refresh function
  const handleRefresh = () => {
    console.log('User requested data refresh');
    loadAllHistory(true);  // Force refresh
  };

  const getRiskClass = (riskLevel: string | null): string => {
    switch (riskLevel?.toLowerCase()) {
      case 'low': return 'risk-low';
      case 'medium': return 'risk-med';
      case 'high': return 'risk-high';
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

  // Only load data when first opening the component
  useEffect(() => {
    if (!isDataLoaded) {
      console.log('First time loading history data');
      loadAllHistory(false);
    }
  }, []);

  // Handle initial search filter from props
  useEffect(() => {
    if (tickerFilter && isDataLoaded) {
      setSearchTicker(tickerFilter);
      performLocalSearch(allHistory, tickerFilter);
    }
  }, [tickerFilter, isDataLoaded]);

  // Apply search when allHistory changes
  useEffect(() => {
    if (isDataLoaded) {
      performLocalSearch(allHistory, searchTicker);
    }
  }, [allHistory, isDataLoaded]);

  if (loading && !isDataLoaded) {
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
      <div className="card shadow-lg mb-4 p-4 sm:p-6">
        <h5 className="mb-4 flex items-center gap-2 text-lg sm:text-xl font-semibold">
          <i className="bi bi-clock-history"></i>
          分析历史
        </h5>

        {/* Real-time Search & Refresh */}
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 mb-4">
          <input
            type="text"
            className="flex-1 px-3 py-2 bg-slate-100 border border-slate-300 rounded-md text-slate-900 placeholder:text-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            placeholder="搜索股票代码... (实时搜索)"
            value={searchTicker}
            onChange={(e) => handleSearchChange(e.target.value.toUpperCase())}
          />
          <Button
            onClick={handleRefresh}
            disabled={loading}
            className={`px-4 py-2 rounded-md font-medium transition-colors whitespace-nowrap ${
              loading
                ? 'bg-gray-100 border-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-orange-600 border-orange-600 text-white hover:bg-orange-700'
            }`}
          >
            <i className={`bi ${loading ? 'bi-arrow-repeat' : 'bi-arrow-clockwise'} mr-2 ${loading ? 'spinner' : ''}`}></i>
            {loading ? '加载中...' : '刷新'}
          </Button>
          <div className="flex items-center gap-2 text-slate-500 text-sm px-2 py-1">
            <i className="bi bi-database"></i>
            <span>{filteredHistory.length}/{allHistory.length} 项</span>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--bear)', color: 'var(--bear)' }}>
            {error}
          </div>
        )}

        {!isDataLoaded ? (
          <div className="text-center py-20 text-muted">
            <i className="bi bi-download text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
            <p>点击"刷新"按钮开始加载历史分析数据</p>
            <Button onClick={handleRefresh} className="btn-primary mt-3">
              <i className="bi bi-arrow-clockwise mr-2"></i>
              加载历史数据
            </Button>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="text-center py-20 text-muted">
            <i className="bi bi-inbox text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
            <p>暂无分析历史记录</p>
          </div>
        ) : (
          <div className="max-h-96 sm:max-h-[600px] overflow-auto">
            {filteredHistory.map((analysisData) => {
              const item = extractDisplayInfo(analysisData);  // Extract display info from complete data

              return (
                <div
                  key={item.id}
                  className="card mb-3 p-4 sm:p-6 cursor-pointer transition-all duration-300 hover:shadow-md"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                      <span className="text-lg sm:text-xl font-bold text-blue-600">
                        {item.ticker}
                      </span>
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">{item.style}</span>
                      {item.risk_level && (
                        <span className={`px-2 py-1 rounded text-xs ${getRiskClass(item.risk_level)}`}>
                          {item.risk_level}
                        </span>
                      )}
                      <span className="px-2 py-1 bg-teal-100 text-teal-800 rounded text-xs">
                        <i className="bi bi-clock-history mr-1"></i>
                        历史分析
                      </span>
                    </div>
                    <span className="text-slate-500 text-sm">
                      {formatDate(item.created_at)}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-3">
                    <div>
                      <div className="text-xs text-slate-500 mb-1">当前价格</div>
                      <div className="text-sm font-medium text-slate-900">
                        {formatCurrency(item.current_price)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">目标价格</div>
                      <div className="text-sm font-medium text-green-600">
                        {formatCurrency(item.target_price)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">风险评分</div>
                      <div className={`text-sm font-medium ${getRiskClass(item.risk_level)}`}>
                        {item.risk_score}/10
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">建议仓位</div>
                      <div className="text-sm font-medium text-blue-600">
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

                  <div className="flex flex-col sm:flex-row gap-2 mt-3">
                    {onViewFullReport && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          loadFullReport(analysisData);  // Pass complete data directly
                        }}
                        className="px-3 py-2 bg-blue-600 border border-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
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
                        className="px-3 py-2 bg-slate-100 border border-slate-300 text-slate-700 rounded-md hover:bg-slate-200 transition-colors text-sm"
                      >
                        <i className="bi bi-arrow-repeat mr-1"></i>
                        重新分析
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
};

export default StockAnalysisHistory;