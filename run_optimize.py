#!/usr/bin/env python3
"""
run_optimize.py — 参数优化网格搜索

用法:
  # 优化 KDJ 参数（以夏普比率为目标）
  python run_optimize.py --indicator KDJ

  # 优化 MACD 参数
  python run_optimize.py --indicator MACD --objective calmar_ratio

  # 自定义参数范围和股票
  python run_optimize.py --indicator KDJ --param-ranges '{"N": [30, 40, 50]}'
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import BacktestConfig
from core.optimizer import ParameterOptimizer
from signals.gf import GFSignal
from config.backtest_config import DEFAULT_CONFIG


# 预置参数网格（每个指标的可优化参数范围）
PRESET_GRIDS = {
    'KDJ':     {'N': [20, 30, 40, 50, 60]},
    'MACD':   {'N1': [10, 12, 14], 'N2': [24, 26, 30], 'N3': [7, 9, 12]},
    'RSI':    {'N': [10, 14, 20, 24, 30]},
    'CCI':    {'N': [10, 14, 20, 30]},
    'WR':     {'N': [6, 10, 14, 20]},
    'ROC':    {'N': [60, 80, 100, 120]},
    'MTM':    {'N': [30, 40, 60, 80]},
    'OBV':    {'N1': [5, 10, 15], 'N2': [20, 30, 40]},
    'BIAS':   {'N': [3, 6, 10]},
    'DPO':    {'N': [10, 15, 20, 25]},
    'KAMA':   {'N': [5, 10, 15], 'N1': [2, 3], 'N2': [20, 25, 30]},
    'TMA':    {'N': [10, 15, 20, 25, 30]},
    'TYP':    {'N1': [5, 10, 15], 'N2': [20, 30, 40]},
    'APZ':    {'N': [5, 10, 15], 'M': [15, 20, 25]},
    'VWAP':   {'N': [10, 15, 20, 25, 30]},
    'VR':     {'N': [20, 30, 40, 50, 60]},
    'ATR':    {'N': [10, 14, 20]},
    'CMF':    {'N': [10, 15, 20, 25]},
    'EMV':    {'N': [10, 14, 20, 30]},
    'FI':     {'N': [9, 13, 20]},
    'PVO':    {'N1': [10, 12, 14], 'N2': [22, 26, 30]},
}


def main():
    parser = argparse.ArgumentParser(description='参数优化网格搜索')
    parser.add_argument('--indicator', type=str, default='KDJ',
                        help='要优化的指标名称，默认 KDJ')
    parser.add_argument('--objective', type=str, default='sharpe_ratio',
                        choices=['total_return', 'annualized_return',
                                 'sharpe_ratio', 'sortino_ratio',
                                 'calmar_ratio', 'win_rate', 'profit_factor'],
                        help='优化目标，默认 sharpe_ratio（夏普比率）')
    parser.add_argument('--param-ranges', type=str, default='',
                        help='自定义参数范围 JSON，如 \'{"N":[30,40,50]}\'')
    parser.add_argument('--stocks', type=str, default='',
                        help='股票代码')
    parser.add_argument('--start', type=str, default='',
                        help='开始日期')
    parser.add_argument('--end', type=str, default='',
                        help='结束日期')
    parser.add_argument('--top-k', type=int, default=5,
                        help='输出最佳组合数，默认5')
    parser.add_argument('--list-grids', action='store_true',
                        help='列出所有预置参数网格')
    args = parser.parse_args()

    if args.list_grids:
        print('\n预置参数网格:')
        for name, grid in sorted(PRESET_GRIDS.items()):
            print(f'  {name}:')
            for param, vals in grid.items():
                print(f'    {param}: {vals}')
        print()
        return

    indicator = args.indicator.upper()

    # 验证指标名
    if indicator not in GFSignal.INDICATORS:
        print(f'错误: 未知指标 "{indicator}"')
        print(f'可用指标共 {len(GFSignal.INDICATORS)} 个，使用 --list-grids 查看预置网格')
        sys.exit(1)

    # 确定参数网格
    if args.param_ranges:
        param_grid = json.loads(args.param_ranges)
    else:
        param_grid = PRESET_GRIDS.get(indicator)
        if param_grid is None:
            print(f'错误: 指标 "{indicator}" 没有预置参数网格')
            print('请通过 --param-ranges 自行指定参数范围')
            sys.exit(1)

    # 基础配置
    cfg = DEFAULT_CONFIG.copy()
    if args.stocks:
        cfg['stock_codes'] = [s.strip() for s in args.stocks.split(',')]
    if args.start:
        cfg['start_date'] = args.start
    if args.end:
        cfg['end_date'] = args.end

    base_output_dir = os.path.join(os.path.dirname(__file__), 'output')
    timestamp = datetime.now().strftime('%Y%m%d/%H%M')
    config = BacktestConfig(
        stock_codes=cfg['stock_codes'],
        start_date=cfg['start_date'],
        end_date=cfg.get('end_date', ''),
        benchmark_code='sh.000300',
        output_dir=os.path.join(base_output_dir, timestamp),
        initial_money_per_stock=cfg.get('initial_money_per_stock', 10000),
        slippage=cfg.get('slippage', 0.003),
        commission_rate=cfg.get('commission_rate', 0.0005),
        tax_rate=cfg.get('tax_rate', 0.001),
        position_pct=cfg.get('position_pct', 0.95),
        risk_free_rate=cfg.get('risk_free_rate', 0.027),
        stop_loss_pct=cfg.get('stop_loss_pct', 0.05),
        stop_profit_pct=cfg.get('stop_profit_pct', 0.20),
        drawdown_pct=cfg.get('drawdown_pct', 0.03),
    )

    # 执行优化（使用与 BacktestConfig 相同的带时间戳输出目录）
    optimizer = ParameterOptimizer(os.path.join(base_output_dir, timestamp))

    optimizer.grid_search(
        signal_class=GFSignal,
        param_grid=param_grid,
        base_config=config,
        objective=args.objective,
        top_k=args.top_k,
        fixed_params={'indicator': indicator},
    )


if __name__ == '__main__':
    main()
