/**
 * Browser localStorage utility for managing analysis history
 */

interface OptionAnalysisHistoryItem {
  id: string;
  symbol: string;
  expiryDate: string;
  timestamp: number;
  analysisType: 'chain' | 'enhanced';
  data: any; // Store the full analysis result
}

class HistoryStorage {
  private static OPTION_HISTORY_KEY = 'optionAnalysisHistory';
  private static MAX_OPTION_HISTORY_ITEMS = 100; // Limit to prevent localStorage bloat

  // Option Analysis History (Browser Cache)
  static saveOptionAnalysis(item: Omit<OptionAnalysisHistoryItem, 'id' | 'timestamp'>): void {
    try {
      const history = this.getOptionHistory();
      const newItem: OptionAnalysisHistoryItem = {
        ...item,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now()
      };

      // Add to beginning and limit size
      history.unshift(newItem);
      if (history.length > this.MAX_OPTION_HISTORY_ITEMS) {
        history.splice(this.MAX_OPTION_HISTORY_ITEMS);
      }

      localStorage.setItem(this.OPTION_HISTORY_KEY, JSON.stringify(history));
    } catch (error) {
      console.warn('Failed to save option analysis to localStorage:', error);
    }
  }

  static getOptionHistory(symbol?: string): OptionAnalysisHistoryItem[] {
    try {
      const stored = localStorage.getItem(this.OPTION_HISTORY_KEY);
      const history = stored ? JSON.parse(stored) : [];

      if (symbol) {
        return history.filter((item: OptionAnalysisHistoryItem) =>
          item.symbol.toUpperCase() === symbol.toUpperCase()
        );
      }

      return history;
    } catch (error) {
      console.warn('Failed to load option analysis history from localStorage:', error);
      return [];
    }
  }

  static deleteOptionAnalysis(id: string): void {
    try {
      const history = this.getOptionHistory();
      const filtered = history.filter(item => item.id !== id);
      localStorage.setItem(this.OPTION_HISTORY_KEY, JSON.stringify(filtered));
    } catch (error) {
      console.warn('Failed to delete option analysis from localStorage:', error);
    }
  }

  static clearOptionHistory(): void {
    try {
      localStorage.removeItem(this.OPTION_HISTORY_KEY);
    } catch (error) {
      console.warn('Failed to clear option analysis history:', error);
    }
  }

  // Utility methods
  static formatTimestamp(timestamp: number): string {
    return new Date(timestamp).toLocaleString();
  }

  static isHistoryAvailable(): boolean {
    return typeof Storage !== 'undefined';
  }
}

export default HistoryStorage;