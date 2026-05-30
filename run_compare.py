#!/usr/bin/env python3
"""
run_compare.py — 多策略横向对比（GF 指标间对比）

用法:
  # 对比 KDJ 和 MACD
  python run_compare.py --strategies KDJ,MACD

  # 对比多个指标
  python run_compare.py --strategies KDJ,RSI,CCI,MACD

  # 自定义股票和时间
  python run_compare.py --strategies KDJ,RSI --stocks 000012,000014 --start 2023-01-01

  # 列出所有可用指标
  python run_compare.py --list
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import BacktestConfig
from core.comparator import StrategyComparator
from signals.gf import GFSignal
from config.backtest_config import DEFAULT_CONFIG


# GF 作为唯一的信号来源
SIGNAL_FACTORY = {'GF': GFSignal}


def main():
    parser = argparse.ArgumentParser(description='多策略横向对比（GF 指标间对比）')
    parser.add_argument('--strategies', type=str, default='',
                        help='指标名称，逗号分隔，如 KDJ,MACD,RSI')
    parser.add_argument('--stocks', type=str, default='',
                        help='股票代码，逗号分隔')
    parser.add_argument('--start', type=str, default='',
                        help='开始日期')
    parser.add_argument('--end', type=str, default='',
                        help='结束日期')
    parser.add_argument('--list', action='store_true',
                        help='列出所有可用的指标')
    parser.add_argument('--money', type=float, default=None,
                        help='每只股票初始资金')
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='止损比例')
    args = parser.parse_args()

    if args.list:
        print(f'\nGF 综合指标 — 共 {len(GFSignal.INDICATORS)} 个:\n')
        for i, name in enumerate(GFSignal.INDICATORS, 1):
            print(f'  {i:3d}. {name}')
        print()
        return

    # 确定指标列表
    if args.strategies:
        names = [s.strip().upper() for s in args.strategies.split(',')]
    else:
        names = ['KDJ', 'RSI', 'MACD', 'CCI']  # 默认对比 4 个常用指标

    # 基础配置
    cfg = DEFAULT_CONFIG.copy()
    if args.stocks:
        cfg['stock_codes'] = [s.strip() for s in args.stocks.split(',')]
    if args.start:
        cfg['start_date'] = args.start
    if args.end:
        cfg['end_date'] = args.end

    config = BacktestConfig(
        stock_codes=cfg['stock_codes'],
        start_date=cfg['start_date'],
        end_date=cfg.get('end_date', ''),
        benchmark_code='sh.000300',
        initial_money_per_stock=args.money or cfg.get('initial_money_per_stock', 10000),
        slippage=cfg.get('slippage', 0.003),
        commission_rate=cfg.get('commission_rate', 0.0005),
        tax_rate=cfg.get('tax_rate', 0.001),
        position_pct=cfg.get('position_pct', 0.95),
        risk_free_rate=cfg.get('risk_free_rate', 0.027),
        stop_loss_pct=args.stop_loss or cfg.get('stop_loss_pct', 0.05),
        stop_profit_pct=cfg.get('stop_profit_pct', 0.20),
        drawdown_pct=cfg.get('drawdown_pct', 0.03),
    )

    # 构建策略列表
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    comparator = StrategyComparator(output_dir)
    strategies = []

    print(f'\n多策略对比 — {len(names)} 个指标 × {len(config.stock_codes)} 只股票')
    print(f'  时间: {config.start_date} → {config.end_date or "最近"}')
    print('=' * 60)

    for name in names:
        if name not in GFSignal.INDICATORS:
            print(f'  ⚠ 跳过未知指标: {name}')
            continue
        strategies.append((name, GFSignal(indicator=name)))

    comparator.compare(strategies, config)
    comparator.report()


if __name__ == '__main__':
    main()
