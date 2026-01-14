"""
独立股票分析模块
提供股票技术分析和基本面分析功能

主要组件:
- core: 核心分析引擎
- strategies: 分析策略
- tests: 独立测试模块
"""

from .core.engine import StockAnalysisEngine

__all__ = ['StockAnalysisEngine']