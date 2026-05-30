"""
002_self_backtest_reborn — 信号策略包

每个策略继承 core.signal_engine.BaseSignal，只需实现 compute(data) 方法。
"""

from .kama import KAMASignal
from .macd_cdtd import MACDCDTDSignal
from .arbr import ARBRSignal
from .boll_dkbl import BOLLDKBLSignal
from .boll_tdcs import BOLLTDCSignal

__all__ = [
    'KAMASignal',
    'MACDCDTDSignal',
    'ARBRSignal',
    'BOLLDKBLSignal',
    'BOLLTDCSignal',
]
