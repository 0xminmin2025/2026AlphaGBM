import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import HistoryStorage from '@/lib/historyStorage';

interface OptionAnalysisHistoryItem {
  id: string;
  symbol: string;
  expiryDate: string;
  timestamp: number;
  analysisType: 'chain' | 'enhanced';
  data: any; // Store the full analysis result
}

interface OptionAnalysisHistoryProps {
  onSelectHistory?: (item: OptionAnalysisHistoryItem) => void;
  onViewFullReport?: (optionData: any) => void;
  symbolFilter?: string;
}

const OptionAnalysisHistory: React.FC<OptionAnalysisHistoryProps> = ({
  onSelectHistory,
  onViewFullReport,
  symbolFilter
}) => {
  const [history, setHistory] = useState<OptionAnalysisHistoryItem[]>([]);
  const [filteredHistory, setFilteredHistory] = useState<OptionAnalysisHistoryItem[]>([]);
  const [searchSymbol, setSearchSymbol] = useState(symbolFilter || '');
  const [selectedDetail, setSelectedDetail] = useState<OptionAnalysisHistoryItem | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const loadHistory = () => {
    if (!HistoryStorage.isHistoryAvailable()) {
      console.warn('LocalStorage is not available');
      return;
    }

    const allHistory = HistoryStorage.getOptionHistory();
    setHistory(allHistory);
    filterHistory(allHistory, searchSymbol);
  };

  const filterHistory = (historyItems: OptionAnalysisHistoryItem[], symbol: string) => {
    let filtered = historyItems;

    if (symbol) {
      filtered = historyItems.filter(item =>
        item.symbol.toUpperCase().includes(symbol.toUpperCase())
      );
    }

    setFilteredHistory(filtered);
    setCurrentPage(1);
  };

  const handleSearch = () => {
    filterHistory(history, searchSymbol);
  };

  const handleDelete = (id: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (confirm('确认删除此条分析记录？')) {
      HistoryStorage.deleteOptionAnalysis(id);
      loadHistory(); // Refresh the display
    }
  };

  const clearAllHistory = () => {
    if (confirm('确认清除所有期权分析历史？')) {
      HistoryStorage.clearOptionHistory();
      loadHistory();
    }
  };

  const getAnalysisTypeLabel = (type: string): string => {
    switch (type) {
      case 'chain': return '期权链分析';
      case 'enhanced': return '增强分析';
      default: return type;
    }
  };

  const getAnalysisTypeClass = (type: string): string => {
    switch (type) {
      case 'chain': return 'text-primary';
      case 'enhanced': return 'text-warning';
      default: return 'text-muted';
    }
  };

  const formatTimestamp = (timestamp: number): string => {
    return HistoryStorage.formatTimestamp(timestamp);
  };

  const getCurrentPageItems = (): OptionAnalysisHistoryItem[] => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredHistory.slice(startIndex, endIndex);
  };

  const getTotalPages = (): number => {
    return Math.ceil(filteredHistory.length / itemsPerPage);
  };

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (symbolFilter !== searchSymbol) {
      setSearchSymbol(symbolFilter || '');
      filterHistory(history, symbolFilter || '');
    }
  }, [symbolFilter, history]);

  if (!HistoryStorage.isHistoryAvailable()) {
    return (
      <div className="card shadow-lg" style={{ padding: '2rem' }}>
        <div className="text-center text-muted">
          <i className="bi bi-exclamation-triangle text-4xl mb-2" style={{ display: 'block' }}></i>
          <p>浏览器不支持本地存储功能</p>
        </div>
      </div>
    );
  }

  const currentItems = getCurrentPageItems();
  const totalPages = getTotalPages();

  return (
    <>
      <div className="card shadow-lg mb-4 p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 mb-4">
          <h5 className="flex items-center gap-2 text-lg sm:text-xl font-semibold m-0">
            <i className="bi bi-clock-history"></i>
            期权分析历史
          </h5>
          {history.length > 0 && (
            <button
              onClick={clearAllHistory}
              className="px-3 py-2 text-sm bg-red-50 border border-red-300 text-red-600 rounded-md hover:bg-red-100 transition-colors whitespace-nowrap"
            >
              <i className="bi bi-trash mr-1"></i>
              清空历史
            </button>
          )}
        </div>

        <p className="text-slate-500 mb-4 text-sm">
          期权分析历史记录（存储在浏览器本地）
        </p>

        {/* Search */}
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 mb-4">
          <input
            type="text"
            className="flex-1 px-3 py-2 bg-slate-100 border border-slate-300 rounded-md text-slate-900 placeholder:text-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            placeholder="搜索标的代码..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button
            onClick={handleSearch}
            className="px-4 py-2 bg-blue-600 border border-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium whitespace-nowrap"
          >
            <i className="bi bi-search mr-2"></i>
            搜索
          </Button>
        </div>

        {filteredHistory.length === 0 ? (
          <div className="text-center py-20 text-muted">
            <i className="bi bi-inbox text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
            <p>{searchSymbol ? '未找到相关记录' : '暂无期权分析历史'}</p>
          </div>
        ) : (
          <div className="max-h-96 sm:max-h-[600px] overflow-auto">
            {currentItems.map((item) => (
              <div
                key={item.id}
                className="card mb-3 p-4 sm:p-6 cursor-pointer transition-all duration-300 hover:shadow-md"
                onClick={() => {
                  setSelectedDetail(item);
                  setShowDetail(true);
                }}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    <span className="text-lg sm:text-xl font-bold text-blue-600">
                      {item.symbol}
                    </span>
                    <span className={`px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs ${getAnalysisTypeClass(item.analysisType)}`}>
                      {getAnalysisTypeLabel(item.analysisType)}
                    </span>
                    <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                      {item.expiryDate}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 justify-between sm:justify-end">
                    <span className="text-slate-500 text-sm">
                      {formatTimestamp(item.timestamp)}
                    </span>
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">分析类型</div>
                    <div className="text-sm font-medium text-slate-900">
                      {getAnalysisTypeLabel(item.analysisType)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">到期日期</div>
                    <div className="text-sm font-medium text-slate-900">
                      {item.expiryDate}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 mt-3">
                  {onSelectHistory && (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectHistory(item);
                      }}
                      className="px-3 py-2 bg-slate-100 border border-slate-300 text-slate-700 rounded-md hover:bg-slate-200 transition-colors text-sm"
                    >
                      <i className="bi bi-arrow-repeat mr-1"></i>
                      重新分析
                    </Button>
                  )}
                  {onViewFullReport && item.data && (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewFullReport(item.data);
                      }}
                      className="px-3 py-2 bg-blue-600 border border-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                    >
                      <i className="bi bi-file-text mr-1"></i>
                      查看完整报告
                    </Button>
                  )}
                </div>
              </div>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-3 pt-4">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className={`p-2 border rounded-md transition-colors ${
                    currentPage === 1
                      ? 'bg-gray-100 border-gray-300 text-gray-400 cursor-not-allowed'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 cursor-pointer'
                  }`}
                >
                  <i className="bi bi-chevron-left"></i>
                </button>

                <span className="text-slate-500 text-sm">
                  第 {currentPage} 页，共 {totalPages} 页
                </span>

                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className={`p-2 border rounded-md transition-colors ${
                    currentPage === totalPages
                      ? 'bg-gray-100 border-gray-300 text-gray-400 cursor-not-allowed'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 cursor-pointer'
                  }`}
                >
                  <i className="bi bi-chevron-right"></i>
                </button>
              </div>
            )}

            <div className="text-center text-slate-500 pt-3 text-xs">
              共 {filteredHistory.length} 条记录 | 数据存储在浏览器本地
            </div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {showDetail && selectedDetail && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowDetail(false)}
        >
          <div
            className="card shadow-lg w-full max-w-4xl max-h-[90vh] overflow-auto p-4 sm:p-6 m-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <h4 className="text-lg sm:text-xl md:text-2xl font-semibold text-blue-600">
                {selectedDetail.symbol} 期权分析详情
              </h4>
              <button
                onClick={() => setShowDetail(false)}
                className="self-end sm:self-center p-1 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors"
              >
                <i className="bi bi-x text-xl"></i>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mb-4">
              <div>
                <div className="text-xs text-slate-500 mb-1">标的代码</div>
                <div className="text-sm font-medium text-blue-600">
                  {selectedDetail.symbol}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">到期日</div>
                <div className="text-sm font-medium text-slate-900">
                  {selectedDetail.expiryDate}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">分析类型</div>
                <div className={`text-sm font-medium ${getAnalysisTypeClass(selectedDetail.analysisType)}`}>
                  {getAnalysisTypeLabel(selectedDetail.analysisType)}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">分析时间</div>
                <div className="text-sm font-medium text-slate-900">
                  {formatTimestamp(selectedDetail.timestamp)}
                </div>
              </div>
            </div>

            <div>
              <h5 className="text-base sm:text-lg font-semibold mb-3 text-slate-900">
                分析结果
              </h5>
              <div className="bg-slate-100 p-3 sm:p-4 rounded-lg text-slate-700 text-sm max-h-64 sm:max-h-96 overflow-auto">
                <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm">
                  {JSON.stringify(selectedDetail.data, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default OptionAnalysisHistory;