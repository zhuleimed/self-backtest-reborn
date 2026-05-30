#!/usr/bin/env python3
"""
002_self_backtest_reborn — 回测入口脚本

用法:
  # 使用预置方案
  python run_backtest.py --plan kama_demo

  # 使用默认方案 (kama_demo)
  python run_backtest.py

  # 自定义参数
  python run_backtest.py --stocks 000012,000014 --start 2022-01-01 --end 2024-12-31
                         --signal KAMA --n 15 --fast 3 --slow 40
                         --stop-loss 0.03 --stop-profit 0.15
"""

import argparse
import sys
import os

# 将项目根目录加入 sys.path（确保 core/ 和 signals/ 可以被导入）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import BacktestEngine, BacktestConfig
from signals.kama import KAMASignal
from signals.macd_cdtd import MACDCDTDSignal
from signals.arbr import ARBRSignal
from signals.boll_dkbl import BOLLDKBLSignal
from signals.boll_tdcs import BOLLTDCSignal
from signals.gf import GFSignal
from config.backtest_config import BACKTEST_PLANS, DEFAULT_CONFIG


# ============================================================================
# 信号工厂：根据名称和参数创建策略实例
# ============================================================================

SIGNAL_FACTORY = {
    'KAMA': KAMASignal,
    'MACD_CDTD': MACDCDTDSignal,
    'ARBR': ARBRSignal,
    'BOLL_DKBL': BOLLDKBLSignal,
    'BOLL_TDCS': BOLLTDCSignal,
    'GF': GFSignal,
}


def create_signal(name: str, params: dict = None):
    """创建信号策略实例"""
    cls = SIGNAL_FACTORY.get(name)
    if cls is None:
        raise ValueError(f'未知信号策略: {name}，可选: {list(SIGNAL_FACTORY.keys())}')
    return cls(**(params or {}))


# ============================================================================
# 命令行参数
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description='模块化量化回测系统 — 002_self_backtest_reborn',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python run_backtest.py --plan kama_demo
  python run_backtest.py --stocks 000012,000014 --signal KAMA
  python run_backtest.py --list-plans
        ''',
    )

    parser.add_argument('--plan', type=str, default='',
                        help='预置回测方案名称（--list-plans 查看所有）')
    parser.add_argument('--list-plans', action='store_true',
                        help='列出所有预置方案')
    parser.add_argument('--stocks', type=str, default='',
                        help='股票代码，逗号分隔，如 000012,000014')
    parser.add_argument('--start', type=str, default='',
                        help='回测开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, default='',
                        help='回测结束日期 YYYY-MM-DD')
    parser.add_argument('--signal', type=str, default='',
                        help='信号策略名称')
    parser.add_argument('--benchmark', type=str, default='',
                        help='基准指数代码')
    parser.add_argument('--tag', type=str, default='',
                        help='回测标识（用于文件命名）')

    # 策略参数
    parser.add_argument('--n', type=int, default=None)
    parser.add_argument('--fast', type=int, default=None)
    parser.add_argument('--slow', type=int, default=None)
    # GF 综合指标参数（选择具体指标）
    parser.add_argument('--indicator', type=str, default='',
                        help='GF信号的具体指标名，如 KDJ, MACD, RSI, CCI 等')

    # 资金参数
    parser.add_argument('--money', type=float, default=None,
                        help='每只股票初始资金')
    parser.add_argument('--slippage', type=float, default=None)
    parser.add_argument('--commission', type=float, default=None)
    parser.add_argument('--tax', type=float, default=None)
    parser.add_argument('--position', type=float, default=None)

    # 风控参数
    parser.add_argument('--stop-loss', type=float, default=None)
    parser.add_argument('--stop-profit', type=float, default=None)
    parser.add_argument('--drawdown', type=float, default=None)

    return parser.parse_args()


# ============================================================================
# 主入口
# ============================================================================

def main():
    args = parse_args()

    # 列出方案
    if args.list_plans:
        print('\n预置回测方案:')
        print('=' * 50)
        for name, plan in BACKTEST_PLANS.items():
            stocks = plan.get('stock_codes', [])
            desc = f'{name:20s} | {plan.get("signal_name")}'
            desc += f' | {len(stocks)} 只 | {plan.get("start_date")}'
            print(f'  {desc}')
        print()
        return

    # 确定配置来源
    if args.plan and args.plan in BACKTEST_PLANS:
        cfg_dict = BACKTEST_PLANS[args.plan].copy()
        print(f'使用预置方案: {args.plan}')
    elif args.plan and args.plan not in BACKTEST_PLANS:
        print(f'错误: 未找到预置方案 "{args.plan}"，使用 --list-plans 查看')
        sys.exit(1)
    else:
        cfg_dict = DEFAULT_CONFIG.copy()
        print(f'使用默认配置')

    # CLI 参数覆盖
    if args.stocks:
        cfg_dict['stock_codes'] = [s.strip() for s in args.stocks.split(',')]
    if args.start:
        cfg_dict['start_date'] = args.start
    if args.end:
        cfg_dict['end_date'] = args.end
    if args.signal:
        cfg_dict['signal_name'] = args.signal
    if args.benchmark:
        cfg_dict['benchmark_code'] = args.benchmark
    if args.money is not None:
        cfg_dict['initial_money_per_stock'] = args.money
    if args.slippage is not None:
        cfg_dict['slippage'] = args.slippage
    if args.commission is not None:
        cfg_dict['commission_rate'] = args.commission
    if args.tax is not None:
        cfg_dict['tax_rate'] = args.tax
    if args.position is not None:
        cfg_dict['position_pct'] = args.position
    if args.stop_loss is not None:
        cfg_dict['stop_loss_pct'] = args.stop_loss
    if args.stop_profit is not None:
        cfg_dict['stop_profit_pct'] = args.stop_profit
    if args.drawdown is not None:
        cfg_dict['drawdown_pct'] = args.drawdown

    # 策略参数覆盖
    signal_params = cfg_dict.get('signal_params', {}).copy()
    if args.n is not None:
        signal_params['n'] = args.n
    if args.fast is not None:
        signal_params['fast'] = args.fast
    if args.slow is not None:
        signal_params['slow'] = args.slow
    # GF 指标参数
    if args.indicator:
        signal_params['indicator'] = args.indicator.upper()

    # 创建策略
    strategy = create_signal(cfg_dict['signal_name'], signal_params)

    # 创建配置对象
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
        tag=args.tag or f'{strategy.name}_{cfg_dict["start_date"]}',
    )

    # 执行回测
    engine = BacktestEngine(config)
    engine.register_signal(strategy)
    metrics = engine.run()

    return metrics


if __name__ == '__main__':
    main()
