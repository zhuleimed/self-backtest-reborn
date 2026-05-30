"""
002_self_backtest_reborn - 模块化量化回测框架

基于 Claude Code 最佳实践的三层架构设计：
  Command → Agent → Skill

核心引擎层（Core）提供可组合的流水线模块：
  DataLoader → SignalEngine → RiskManager → EquityCurve → Metrics → Reporter
"""

from .data_loader import DataLoader
from .signal_engine import SignalEngine, BaseSignal
from .risk_manager import RiskManager
from .equity_curve import EquityCurveCalculator, BacktestParams, TradeRecord
from .metrics import MetricsCalculator, BacktestMetrics
from .reporter import Reporter
from .engine import BacktestEngine, BacktestConfig
from .comparator import StrategyComparator, ComparisonResult
from .optimizer import ParameterOptimizer, ParamGridResult

__all__ = [
    'DataLoader',
    'SignalEngine',
    'BaseSignal',
    'RiskManager',
    'EquityCurveCalculator',
    'BacktestParams',
    'TradeRecord',
    'MetricsCalculator',
    'BacktestMetrics',
    'Reporter',
    'BacktestEngine',
    'BacktestConfig',
    'StrategyComparator',
    'ComparisonResult',
    'ParameterOptimizer',
    'ParamGridResult',
]
