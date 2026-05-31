"""
002_self_backtest_reborn — 信号策略包

全部技术指标统一从 GF 综合策略导入（gf.py + gf_factors.py）。
独立信号模块已整合进 GF，不再单独维护。
"""

from .gf import GFSignal, ComboGFSignal

__all__ = ['GFSignal', 'ComboGFSignal']
