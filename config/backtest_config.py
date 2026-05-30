"""
回测配置中心

所有可配置项集中在此，方便批量管理回测方案。
使用方式：直接修改本文件中的配置字典，或通过 CLI 参数覆盖。
"""

from typing import Dict, List

# ============================================================================
# 常用股票池
# ============================================================================

STOCK_POOLS: Dict[str, List[str]] = {
    'demo': [
        '000012', '000014', '000016', '000050',
        '000055', '000062', '000070',
    ],
    'sz50_sample': [
        '000001', '000002', '000004', '000006', '000008',
        '000009', '000010', '000011', '000012', '000016',
    ],
    'hs300_sample': [
        '000001', '000002', '000006', '000008', '000012',
        '000016', '000021', '000025', '000027', '000028',
        '000030', '000031', '000034', '000035', '000036',
        '000039', '000040', '000046', '000049', '000050',
    ],
}

# ============================================================================
# 预置回测方案
# ============================================================================

BACKTEST_PLANS: Dict[str, Dict] = {
    # ---- KAMA 策略 ----
    'kama_demo': {
        'stock_codes': STOCK_POOLS['demo'],
        'start_date': '2022-01-01',
        'end_date': '',
        'benchmark_code': 'sh.000300',
        'signal_name': 'KAMA',
        'signal_params': {'n': 10, 'fast': 2, 'slow': 30},
        # 资金参数
        'initial_money_per_stock': 10000,
        'slippage': 0.003,
        'commission_rate': 5.0 / 10000,
        'tax_rate': 1.0 / 1000,
        'position_pct': 0.95,
        'risk_free_rate': 0.027,
        # 风控
        'stop_loss_pct': 0.05,
        'stop_profit_pct': 0.20,
        'drawdown_pct': 0.03,
    },

    # ---- KAMA 沪深300样本 ----
    'kama_hs300': {
        'stock_codes': STOCK_POOLS['hs300_sample'],
        'start_date': '2020-01-01',
        'end_date': '',
        'benchmark_code': 'sh.000300',
        'signal_name': 'KAMA',
        'signal_params': {'n': 10, 'fast': 2, 'slow': 30},
        'initial_money_per_stock': 10000,
        'slippage': 0.003,
        'commission_rate': 5.0 / 10000,
        'tax_rate': 1.0 / 1000,
        'position_pct': 0.95,
        'risk_free_rate': 0.027,
        'stop_loss_pct': 0.05,
        'stop_profit_pct': 0.20,
        'drawdown_pct': 0.03,
    },

    # ---- KAMA 严格止盈 ----
    'kama_tight_stop': {
        'stock_codes': STOCK_POOLS['demo'],
        'start_date': '2022-01-01',
        'end_date': '',
        'benchmark_code': 'sh.000300',
        'signal_name': 'KAMA',
        'signal_params': {'n': 10, 'fast': 2, 'slow': 30},
        'initial_money_per_stock': 10000,
        'slippage': 0.003,
        'commission_rate': 5.0 / 10000,
        'tax_rate': 1.0 / 1000,
        'position_pct': 0.95,
        'risk_free_rate': 0.027,
        'stop_loss_pct': 0.03,    # 3%止损
        'stop_profit_pct': 0.10,  # 10%止盈
        'drawdown_pct': 0.02,     # 2%回落
    },

    # ---- BOLL_DKBL 带宽收口策略 ----
    'boll_dkbl_demo': {
        'stock_codes': STOCK_POOLS['demo'],
        'start_date': '2022-01-01',
        'end_date': '',
        'benchmark_code': 'sh.000300',
        'signal_name': 'BOLL_DKBL',
        'signal_params': {'period': 20, 'std_multiplier': 2.0, 'volume_ratio': 1.5},
        'initial_money_per_stock': 10000,
        'slippage': 0.003,
        'commission_rate': 5.0 / 10000,
        'tax_rate': 1.0 / 1000,
        'position_pct': 0.95,
        'risk_free_rate': 0.027,
        'stop_loss_pct': 0.05,
        'stop_profit_pct': 0.20,
        'drawdown_pct': 0.03,
    },

    # ---- BOLL_TDCS 布林参数调优策略 ----
    'boll_tdcs_demo': {
        'stock_codes': STOCK_POOLS['demo'],
        'start_date': '2022-01-01',
        'end_date': '',
        'benchmark_code': 'sh.000300',
        'signal_name': 'BOLL_TDCS',
        'signal_params': {'period': 20, 'std_multiplier': 2.0, 'use_all_signals': True},
        'initial_money_per_stock': 10000,
        'slippage': 0.003,
        'commission_rate': 5.0 / 10000,
        'tax_rate': 1.0 / 1000,
        'position_pct': 0.95,
        'risk_free_rate': 0.027,
        'stop_loss_pct': 0.05,
        'stop_profit_pct': 0.20,
        'drawdown_pct': 0.03,
    },
}

# ============================================================================
# 默认配置
# ============================================================================

# ============================================================================
# 默认配置
# ============================================================================

DEFAULT_CONFIG = BACKTEST_PLANS['kama_demo']
