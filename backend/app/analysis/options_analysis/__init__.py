"""
独立期权分析模块
提供期权链分析、策略计分、VRP风险分析等功能

主要组件:
- core: 核心分析引擎和数据获取
- scoring: 期权策略计分算法 (sell put/call, buy put/call)
- advanced: 高级分析 (VRP, Risk)
- tests: 独立测试模块
"""

from .core.engine import OptionsAnalysisEngine

__all__ = ['OptionsAnalysisEngine']