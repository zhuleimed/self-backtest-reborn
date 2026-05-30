#!/usr/bin/env python3
"""
run_optimize.py — 参数优化网格搜索

用法:
  # KAMA 策略参数优化
  python run_optimize.py --strategy KAMA --objective sharpe_ratio

  # 指定参数范围
  python run_optimize.py --strategy KAMA --param-ranges '{"n": [5,10,15,20], "fast": [2,3], "slow": [20,25,30,35]}'

  # 指定目标函数
  python run_optimize.py --strategy KAMA --objective calmar_ratio --top-k 10
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import BacktestConfig
from core.optimizer import ParameterOptimizer
from config.backtest_config import DEFAULT_CONFIG
from run_backtest import SIGNAL_FACTORY, create_signal


# 预置参数网格
PRESET_GRIDS = {
    'KAMA': {
        'n': [5, 10, 15, 20, 30],
        'fast': [2, 3],
        'slow': [20, 25, 30, 35, 40],
    },
    'MACD_CDTD': {
        'fast_period': [10, 12, 14],
        'slow_period': [24, 26, 30],
        'signal_period': [7, 9, 12],
    },
    'ARBR': {
        'period': [20, 26, 30],
        'ar_threshold': [130, 150, 170],
        'br_threshold': [40, 50, 60],
    },
    'BOLL_DKBL': {
        'period': [15, 20, 25, 30],
        'std_multiplier': [1.8, 2.0, 2.2],
        'volume_ratio': [1.3, 1.5, 1.8],
    },
    'BOLL_TDCS': {
        'period': [15, 20, 25, 30],
        'std_multiplier': [1.8, 2.0, 2.2],
    },
}


def main():
    parser = argparse.ArgumentParser(description='参数优化网格搜索')
    parser.add_argument('--strategy', type=str, default='KAMA',
                        help='信号策略名称')
    parser.add_argument('--objective', type=str, default='sharpe_ratio',
                        choices=['total_return', 'annualized_return',
                                 'sharpe_ratio', 'sortino_ratio',
                                 'calmar_ratio', 'win_rate', 'profit_factor'],
                        help='优化目标')
    parser.add_argument('--param-ranges', type=str, default='',
                        help='自定义参数范围 JSON，如 \'{"n":[5,10]}\'')
    parser.add_argument('--stocks', type=str, default='',
                        help='股票代码')
    parser.add_argument('--start', type=str, default='',
                        help='开始日期')
    parser.add_argument('--top-k', type=int, default=5,
                        help='输出最佳组合数')
    parser.add_argument('--list-grids', action='store_true',
                        help='列出所有预置参数网格')
    args = parser.parse_args()

    if args.list_grids:
        print('\n预置参数网格:')
        for name, grid in PRESET_GRIDS.items():
            print(f'  {name}:')
            for param, vals in grid.items():
                print(f'    {param}: {vals}')
        print()
        return

    if args.strategy not in SIGNAL_FACTORY:
        print(f'错误: 未知策略 "{args.strategy}"')
        print(f'可选: {list(SIGNAL_FACTORY.keys())}')
        sys.exit(1)

    # 确定参数网格
    if args.param_ranges:
        param_grid = json.loads(args.param_ranges)
    else:
        param_grid = PRESET_GRIDS.get(args.strategy)
        if param_grid is None:
            print(f'错误: 策略 "{args.strategy}" 没有预置参数网格')
            print('请通过 --param-ranges 指定参数范围')
            sys.exit(1)

    # 基础配置
    cfg_dict = DEFAULT_CONFIG.copy()
    if args.stocks:
        cfg_dict['stock_codes'] = [s.strip() for s in args.stocks.split(',')]
    if args.start:
        cfg_dict['start_date'] = args.start

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

    # 执行优化
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    optimizer = ParameterOptimizer(output_dir)

    optimizer.grid_search(
        signal_class=SIGNAL_FACTORY[args.strategy],
        param_grid=param_grid,
        base_config=config,
        objective=args.objective,
        top_k=args.top_k,
    )


if __name__ == '__main__':
    main()
