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
      <div className="card shadow-lg mb-4" style={{ padding: '1.5rem' }}>
        <div className="flex items-center justify-between mb-4">
          <h5 className="flex items-center gap-2" style={{ fontSize: '1.3rem', fontWeight: 600, margin: 0 }}>
            <i className="bi bi-clock-history"></i>
            期权分析历史
          </h5>
          {history.length > 0 && (
            <button
              onClick={clearAllHistory}
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid var(--bear)',
                color: 'var(--bear)',
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              <i className="bi bi-trash mr-1"></i>
              清空历史
            </button>
          )}
        </div>

        <p className="text-muted mb-4" style={{ fontSize: '0.9rem' }}>
          期权分析历史记录（存储在浏览器本地）
        </p>

        {/* Search */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4 mb-4">
          <input
            type="text"
            className="form-control"
            placeholder="搜索标的代码..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
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

        {filteredHistory.length === 0 ? (
          <div className="text-center py-20 text-muted">
            <i className="bi bi-inbox text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
            <p>{searchSymbol ? '未找到相关记录' : '暂无期权分析历史'}</p>
          </div>
        ) : (
          <div style={{ maxHeight: '600px', overflow: 'auto' }}>
            {currentItems.map((item) => (
              <div
                key={item.id}
                className="card mb-3"
                style={{
                  padding: '1.5rem',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease'
                }}
                onClick={() => {
                  setSelectedDetail(item);
                  setShowDetail(true);
                }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                      {item.symbol}
                    </span>
                    <span className={`badge-primary ${getAnalysisTypeClass(item.analysisType)}`}>
                      {getAnalysisTypeLabel(item.analysisType)}
                    </span>
                    <span className="badge-primary" style={{ fontSize: '0.8rem' }}>
                      {item.expiryDate}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted" style={{ fontSize: '0.9rem' }}>
                      {formatTimestamp(item.timestamp)}
                    </span>
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--bear)',
                        cursor: 'pointer',
                        padding: '0.25rem',
                        borderRadius: '4px',
                        fontSize: '0.9rem'
                      }}
                      onMouseOver={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.1)'}
                      onMouseOut={(e) => e.target.style.background = 'none'}
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <div className="metric-label">分析类型</div>
                    <div className="metric-value" style={{ fontSize: '1rem', color: 'var(--foreground)' }}>
                      {getAnalysisTypeLabel(item.analysisType)}
                    </div>
                  </div>
                  <div>
                    <div className="metric-label">到期日期</div>
                    <div className="metric-value" style={{ fontSize: '1rem', color: 'var(--foreground)' }}>
                      {item.expiryDate}
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 mt-3">
                  {onSelectHistory && (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectHistory(item);
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
                  {onViewFullReport && item.data && (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewFullReport(item.data);
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
                  style={{
                    background: currentPage === 1 ? 'var(--muted)' : 'var(--card)',
                    border: '1px solid var(--border)',
                    color: currentPage === 1 ? 'var(--muted-foreground)' : 'var(--foreground)',
                    padding: '0.5rem',
                    borderRadius: '6px',
                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                  }}
                >
                  <i className="bi bi-chevron-left"></i>
                </button>

                <span className="text-muted" style={{ fontSize: '0.9rem' }}>
                  第 {currentPage} 页，共 {totalPages} 页
                </span>

                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  style={{
                    background: currentPage === totalPages ? 'var(--muted)' : 'var(--card)',
                    border: '1px solid var(--border)',
                    color: currentPage === totalPages ? 'var(--muted-foreground)' : 'var(--foreground)',
                    padding: '0.5rem',
                    borderRadius: '6px',
                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'
                  }}
                >
                  <i className="bi bi-chevron-right"></i>
                </button>
              </div>
            )}

            <div className="text-center text-muted pt-3" style={{ fontSize: '0.8rem' }}>
              共 {filteredHistory.length} 条记录 | 数据存储在浏览器本地
            </div>
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
                {selectedDetail.symbol} 期权分析详情
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

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="metric-label">标的代码</div>
                <div className="metric-value" style={{ color: 'var(--primary)' }}>
                  {selectedDetail.symbol}
                </div>
              </div>
              <div>
                <div className="metric-label">到期日</div>
                <div className="metric-value" style={{ color: 'var(--foreground)' }}>
                  {selectedDetail.expiryDate}
                </div>
              </div>
              <div>
                <div className="metric-label">分析类型</div>
                <div className={`metric-value ${getAnalysisTypeClass(selectedDetail.analysisType)}`}>
                  {getAnalysisTypeLabel(selectedDetail.analysisType)}
                </div>
              </div>
              <div>
                <div className="metric-label">分析时间</div>
                <div className="metric-value" style={{ color: 'var(--foreground)' }}>
                  {formatTimestamp(selectedDetail.timestamp)}
                </div>
              </div>
            </div>

            <div>
              <h5 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: 'var(--foreground)' }}>
                分析结果
              </h5>
              <div
                style={{
                  background: 'var(--muted)',
                  padding: '1rem',
                  borderRadius: '8px',
                  color: 'var(--muted-foreground)',
                  fontSize: '0.85rem',
                  maxHeight: '400px',
                  overflow: 'auto'
                }}
              >
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
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