import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useTranslation } from 'react-i18next';

// Each history item contains the complete options analysis data
interface CompleteOptionsAnalysisData {
  success: boolean;
  data: any;  // Complete options chain/enhanced analysis data
  vrp_analysis?: any;  // VRP analysis for enhanced
  risk_analysis?: any;  // Risk analysis for enhanced
  report: string;  // AI analysis report
  history_metadata: {
    id: number;
    created_at: string;
    is_from_history: boolean;
    symbol: string;
    option_identifier?: string;
    expiry_date?: string;
    analysis_type: string;  // 'basic_chain' or 'enhanced_analysis'
    incomplete_data?: boolean;
  };
}

interface OptionsAnalysisHistoryProps {
  onSelectHistory?: (symbol: string, analysisType: string, optionIdentifier?: string, expiryDate?: string) => void;
  onViewFullReport?: (analysisData: CompleteOptionsAnalysisData) => void;
  symbolFilter?: string;
}

const OptionsAnalysisHistory: React.FC<OptionsAnalysisHistoryProps> = ({
  onSelectHistory,
  onViewFullReport,
  symbolFilter
}) => {
  const { t } = useTranslation();
  const [allHistory, setAllHistory] = useState<CompleteOptionsAnalysisData[]>([]);  // Cache all loaded data
  const [filteredHistory, setFilteredHistory] = useState<CompleteOptionsAnalysisData[]>([]);  // Filtered data for display
  const [loading, setLoading] = useState(false);  // Start as false, load on demand
  const [error, setError] = useState<string | null>(null);
  const [isDataLoaded, setIsDataLoaded] = useState(false);  // Track if data has been loaded
  const [searchSymbol, setSearchSymbol] = useState(symbolFilter || '');

  // Load all historical data (only when user explicitly requests or first time)
  const loadAllHistory = async (forceRefresh: boolean = false) => {
    if (isDataLoaded && !forceRefresh) {
      console.log('Options history already loaded, skipping network request');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Load a large amount of data to minimize requests (get more at once)
      const allData: CompleteOptionsAnalysisData[] = [];
      let currentPage = 1;
      let hasMoreData = true;

      while (hasMoreData && currentPage <= 10) { // Limit to prevent infinite loading
        const params = new URLSearchParams({
          page: currentPage.toString(),
          per_page: '50'  // Get 50 items per page for efficient loading
        });

        const response = await api.get(`/options/history?${params}`);

        if (response.data.success) {
          const newItems = response.data.data.items;
          allData.push(...newItems);
          hasMoreData = response.data.data.pagination.has_next;
          currentPage++;

          console.log(`Loaded options page ${currentPage - 1}, items: ${newItems.length}, total: ${allData.length}`);
        } else {
          throw new Error(response.data.error || 'Failed to load options history');
        }
      }

      setAllHistory(allData);
      setIsDataLoaded(true);
      console.log(`Completed loading options history: ${allData.length} total items`);

      // Apply current search filter
      performLocalSearch(allData, searchSymbol);

    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load options analysis history');
    } finally {
      setLoading(false);
    }
  };

  // Perform local search on cached data (real-time, no network request)
  const performLocalSearch = (dataToSearch: CompleteOptionsAnalysisData[], searchQuery: string) => {
    if (!searchQuery.trim()) {
      setFilteredHistory(dataToSearch);
      return;
    }

    const query = searchQuery.toUpperCase().trim();
    const filtered = dataToSearch.filter(analysisData => {
      const symbol = analysisData.history_metadata?.symbol || '';
      const optionIdentifier = analysisData.history_metadata?.option_identifier || '';
      return symbol.toUpperCase().includes(query) || optionIdentifier.toUpperCase().includes(query);
    });

    setFilteredHistory(filtered);
    console.log(`Local search for "${searchQuery}": ${filtered.length} options results found`);
  };

  // Extract display info from complete options analysis data
  const extractDisplayInfo = (analysisData: CompleteOptionsAnalysisData) => {
    const metadata = analysisData.history_metadata;
    const data = analysisData.data || {};

    return {
      id: metadata.id,
      symbol: metadata.symbol,
      option_identifier: metadata.option_identifier,
      expiry_date: metadata.expiry_date,
      analysis_type: metadata.analysis_type,
      // For basic chain analysis
      strike_price: data.strike_price || null,
      option_type: data.option_type || null,
      option_score: data.option_score || null,
      iv_rank: data.iv_rank || null,
      // For enhanced analysis
      vrp_analysis: analysisData.vrp_analysis || null,
      risk_analysis: analysisData.risk_analysis || null,
      ai_summary: analysisData.report ? analysisData.report.substring(0, 200) + '...' : null,
      created_at: metadata.created_at
    };
  };

  // Load full report directly from memory (no network request)
  const loadFullReport = (analysisData: CompleteOptionsAnalysisData) => {
    if (onViewFullReport) {
      console.log('Loading complete historical options analysis from memory:', analysisData);
      // Pass the complete analysis data directly to parent
      onViewFullReport(analysisData);
    }
  };

  // Handle real-time search input changes
  const handleSearchChange = (newSearchValue: string) => {
    setSearchSymbol(newSearchValue);
    // Perform local search immediately on cached data
    performLocalSearch(allHistory, newSearchValue);
  };

  // Manual refresh function
  const handleRefresh = () => {
    console.log('User requested options data refresh');
    loadAllHistory(true);  // Force refresh
  };

  const formatCurrency = (value: number | null): string => {
    if (value === null || value === undefined) return 'N/A';
    return `$${value.toFixed(2)}`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _getAnalysisTypeLabel = (analysisType: string): string => {
    switch (analysisType) {
      case 'basic_chain': return t('options.history.analysisType.chain');
      case 'enhanced_analysis': return t('options.history.analysisType.enhanced');
      default: return analysisType;
    }
  };

  // Only load data when first opening the component
  useEffect(() => {
    if (!isDataLoaded) {
      console.log('First time loading options history data');
      loadAllHistory(false);
    }
  }, []);

  // Handle initial search filter from props
  useEffect(() => {
    if (symbolFilter && isDataLoaded) {
      setSearchSymbol(symbolFilter);
      performLocalSearch(allHistory, symbolFilter);
    }
  }, [symbolFilter, isDataLoaded]);

  // Apply search when allHistory changes
  useEffect(() => {
    if (isDataLoaded) {
      performLocalSearch(allHistory, searchSymbol);
    }
  }, [allHistory, isDataLoaded]);

  if (loading && !isDataLoaded) {
    return (
      <div className="card shadow-lg" style={{ padding: '2rem' }}>
        <div className="text-center">
          <div className="spinner" style={{ margin: '0 auto 1rem' }}></div>
          <p style={{ color: 'var(--muted-foreground)' }}>{t('options.history.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="card bg-[#0f0f11] border-white/10 shadow-lg mb-4 p-4 sm:p-6">
        <h5 className="mb-4 flex items-center gap-2 text-lg sm:text-xl font-semibold">
          <i className="bi bi-clock-history"></i>
          {t('options.history.title')}
        </h5>

        {/* Real-time Search & Refresh */}
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 mb-4">
          <input
            type="text"
            className="flex-1 px-3 py-2 bg-[#27272a] border border-white/20 rounded-md text-white placeholder:text-slate-400 focus:border-[#0D9B97] focus:ring-2 focus:ring-[#0D9B97]/20"
            placeholder={t('options.history.searchPlaceholder')}
            value={searchSymbol}
            onChange={(e) => handleSearchChange(e.target.value.toUpperCase())}
          />
          <Button
            onClick={handleRefresh}
            disabled={loading}
            className={`px-4 py-2 rounded-md font-medium transition-colors whitespace-nowrap ${
              loading
                ? 'bg-white/5 border-white/10 text-slate-600 cursor-not-allowed'
                : 'bg-[#0D9B97] border-[#0D9B97] text-white hover:bg-[#0D9B97]/80'
            }`}
          >
            <i className={`bi ${loading ? 'bi-arrow-repeat' : 'bi-arrow-clockwise'} mr-2 ${loading ? 'spinner' : ''}`}></i>
            {loading ? t('options.history.refreshing') : t('options.history.refresh')}
          </Button>
          <div className="flex items-center gap-2 text-slate-400 text-sm px-2 py-1">
            <i className="bi bi-database"></i>
            <span>{filteredHistory.length}/{allHistory.length} {t('options.history.items')}</span>
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
            <p>{t('options.history.loadPrompt')}</p>
            <Button onClick={handleRefresh} className="btn-primary mt-3">
              <i className="bi bi-arrow-clockwise mr-2"></i>
              {t('options.history.loadButton')}
            </Button>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="text-center py-20 text-muted">
            <i className="bi bi-inbox text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
            <p>{t('options.history.noRecords')}</p>
          </div>
        ) : (
          <div className="max-h-[500px] sm:max-h-[700px] overflow-auto">
            {filteredHistory.map((analysisData) => {
              const item = extractDisplayInfo(analysisData);  // Extract display info from complete data

              return (
                <div
                  key={item.id}
                  className="card bg-[#1c1c1e] border-white/10 mb-3 p-4 sm:p-6 cursor-pointer transition-all duration-300 hover:bg-[#1c1c1e]/80 hover:border-[#0D9B97]/30"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                      <span className="text-lg sm:text-xl font-bold text-[#0D9B97]">
                        {item.symbol}
                      </span>
                      {item.expiry_date && (
                        <span className="px-2 py-1 bg-white/10 text-slate-300 rounded text-xs">
                          {t('options.history.expiryDate')}: {item.expiry_date}
                        </span>
                      )}
                      <span className="px-2 py-1 bg-white/10 text-slate-300 rounded text-xs">
                        <i className="bi bi-clock-history mr-1"></i>
                        {t('options.history.historicalAnalysis')}
                      </span>
                    </div>
                    <span className="text-slate-400 text-sm">
                      {formatDate(item.created_at)}
                    </span>
                  </div>

                  {/* Only show details for basic_chain analysis (the only type we actually use) */}
                  {item.analysis_type === 'basic_chain' && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-3">
                      {item.strike_price && (
                        <div>
                          <div className="text-xs text-slate-500 mb-1">{t('options.history.strikePrice')}</div>
                          <div className="text-sm font-medium text-slate-300">
                            {formatCurrency(item.strike_price)}
                          </div>
                        </div>
                      )}
                      {item.option_type && (
                        <div>
                          <div className="text-xs text-slate-500 mb-1">{t('options.history.optionType')}</div>
                          <div className={`text-sm font-medium ${item.option_type === 'call' ? 'text-green-400' : 'text-red-400'}`}>
                            {item.option_type === 'call' ? 'Call' : 'Put'}
                          </div>
                        </div>
                      )}
                      {item.option_score && (
                        <div>
                          <div className="text-xs text-slate-500 mb-1">{t('options.history.optionScore')}</div>
                          <div className="text-sm font-medium text-[#0D9B97]">
                            {item.option_score}/10
                          </div>
                        </div>
                      )}
                      {item.iv_rank && (
                        <div>
                          <div className="text-xs text-slate-500 mb-1">{t('options.history.ivRank')}</div>
                          <div className="text-sm font-medium text-purple-400">
                            {item.iv_rank}%
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {item.ai_summary && (
                    <div className="text-slate-400" style={{
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
                        className="px-3 py-2 bg-[#0D9B97] border border-[#0D9B97] text-white rounded-md hover:bg-[#0D9B97]/80 transition-colors text-sm"
                      >
                        <i className="bi bi-file-earmark-text mr-1"></i>
                        {t('options.history.viewReport')}
                      </Button>
                    )}
                    {onSelectHistory && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectHistory(
                            item.symbol,
                            item.analysis_type,
                            item.option_identifier,
                            item.expiry_date
                          );
                        }}
                        className="px-3 py-2 bg-white/10 border border-white/20 text-slate-300 rounded-md hover:bg-white/20 transition-colors text-sm"
                      >
                        <i className="bi bi-arrow-repeat mr-1"></i>
                        {t('options.history.reanalyze')}
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

export default OptionsAnalysisHistory;