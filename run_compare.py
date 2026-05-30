#!/usr/bin/env python3
"""
run_compare.py — 多策略横向对比

用法:
  # 对比所有策略（使用默认股票池）
  python run_compare.py

  # 对比指定的几个策略
  python run_compare.py --strategies KAMA,MACD_CDTD,ARBR

  # 自定义股票和时间
  python run_compare.py --stocks 000012,000014 --start 2023-01-01
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import BacktestConfig
from core.comparator import StrategyComparator
from config.backtest_config import BACKTEST_PLANS, DEFAULT_CONFIG
from run_backtest import SIGNAL_FACTORY, create_signal


def main():
    parser = argparse.ArgumentParser(description='多策略横向对比')
    parser.add_argument('--strategies', type=str, default='',
                        help='策略名称，逗号分隔，如 KAMA,MACD_CDTD,ARBR')
    parser.add_argument('--stocks', type=str, default='',
                        help='股票代码，逗号分隔')
    parser.add_argument('--start', type=str, default='',
                        help='开始日期')
    parser.add_argument('--end', type=str, default='',
                        help='结束日期')
    parser.add_argument('--list', action='store_true',
                        help='列出所有可用的策略')
    args = parser.parse_args()

    if args.list:
        print('\n可用的信号策略:')
        for name in SIGNAL_FACTORY:
            print(f'  {name}')
        print()
        return

    # 确定策略列表
    if args.strategies:
        names = [s.strip() for s in args.strategies.split(',')]
    else:
        names = list(SIGNAL_FACTORY.keys())

    # 基础配置
    cfg_dict = DEFAULT_CONFIG.copy()
    if args.stocks:
        cfg_dict['stock_codes'] = [s.strip() for s in args.stocks.split(',')]
    if args.start:
        cfg_dict['start_date'] = args.start
    if args.end:
        cfg_dict['end_date'] = args.end

    config = BacktestConfig(
        stock_codes=cfg_dict['stock_codes'],
        start_date=cfg_dict['start_date'],
        end_date=cfg_dict.get('end_date', ''),
        benchmark_code=cfg_dict.get('benchmark_code', 'sh.000300'),
        initial_money_per_stock=cfg_dict['initial_money_per_stock'],
        slippage=cfg_dict['slippage'],
        commission_rate=cfg_dict['commission_rate'],
        tax_rate=cfg_dict['tax_rate'],
        position_pct=cfg_dict['position_pct'],
        risk_free_rate=cfg_dict.get('risk_free_rate', 0.027),
        stop_loss_pct=cfg_dict['stop_loss_pct'],
        stop_profit_pct=cfg_dict['stop_profit_pct'],
        drawdown_pct=cfg_dict['drawdown_pct'],
    )

    # 构建策略列表
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    comparator = StrategyComparator(output_dir)
    strategies = []

    print(f'\n多策略对比 — {len(names)} 个策略 × {len(config.stock_codes)} 只股票')
    print(f'  时间: {config.start_date} → {config.end_date or "最近"}')
    print('=' * 60)

    for name in names:
        if name not in SIGNAL_FACTORY:
            print(f'  ⚠ 跳过未知策略: {name}')
            continue
        strategies.append((name, create_signal(name)))

    comparator.compare(strategies, config)
    comparator.report()


if __name__ == '__main__':
    main()
