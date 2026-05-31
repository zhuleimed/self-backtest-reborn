#!/usr/bin/env python3
"""
002_self_backtest_reborn — 回测入口脚本

用法:
  # 最简用法（KDJ指标，单只股票）
  python run_backtest.py --stocks 000012 --indicator KDJ

  # 完整自定义
  python run_backtest.py \\
    --stocks 000012,000014 \\
    --start 2022-01-01 \\
    --end 2024-12-31 \\
    --indicator MACD \\
    --money 50000 \\
    --stop-loss 0.03

  # 多指标组合（所有指标同时买入才买入，任一卖出即卖出）
  python run_backtest.py \\
    --stocks 000012 \\
    --indicators KDJ,RSI,MACD \\
    --combo-mode strict_buy

  # 查看所有可用指标
  python run_backtest.py --list-indicators
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import BacktestEngine, BacktestConfig
from signals.gf import GFSignal, ComboGFSignal
from config.backtest_config import DEFAULT_CONFIG


# ============================================================================
# 命令行参数
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description='模块化量化回测系统 — 002_self_backtest_reborn',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python run_backtest.py --stocks 000012 --indicator KDJ
  python run_backtest.py --stocks 000012,000014 --indicator MACD
  python run_backtest.py --list-indicators
        ''',
    )

    parser.add_argument('--list-plans', action='store_true',
                        help='（已弃用）保留兼容')
    parser.add_argument('--list-indicators', action='store_true',
                        help='列出所有可用技术指标（97个）')
    parser.add_argument('--stocks', type=str, default='',
                        help='【必填】股票代码，多只逗号分隔，如 000012,000014')
    parser.add_argument('--start', type=str, default='',
                        help='【可选】回测开始日期 YYYY-MM-DD，默认 2022-01-01')
    parser.add_argument('--end', type=str, default='',
                        help='【可选】回测结束日期 YYYY-MM-DD，不填则到最新数据')
    parser.add_argument('--indicator', type=str, default='KDJ',
                        help='【可选】单个技术指标名称（大写），默认 KDJ。查看全部: --list-indicators')
    parser.add_argument('--indicators', type=str, default='',
                        help='【可选】多指标组合，逗号分隔，如 KDJ,RSI,MACD。'
                             '配合 --combo-mode 使用')
    parser.add_argument('--combo-mode', type=str, default='all_agree',
                        choices=['all_agree', 'strict_buy'],
                        help='【可选】多指标组合模式: all_agree(严格) / strict_buy(宽松买+严格卖)')
    parser.add_argument('--tag', type=str, default='',
                        help='【可选】回测标识，用于输出文件命名')

    # 策略参数
    parser.add_argument('--n', type=int, default=None,
                        help='【可选】指标参数 N（周期），具体含义取决于指标')
    parser.add_argument('--n1', type=int, default=None,
                        help='【可选】指标参数 N1')
    parser.add_argument('--n2', type=int, default=None,
                        help='【可选】指标参数 N2')
    parser.add_argument('--n3', type=int, default=None,
                        help='【可选】指标参数 N3')
    parser.add_argument('--m', type=int, default=None,
                        help='【可选】指标参数 M')

    # 资金参数
    parser.add_argument('--money', type=float, default=None,
                        help='【可选】每只股票初始资金，默认10000元')
    parser.add_argument('--slippage', type=float, default=None,
                        help='【可选】滑点，默认0.003（0.3%%）')
    parser.add_argument('--commission', type=float, default=None,
                        help='【可选】佣金比例，默认0.0005（万分之五）')
    parser.add_argument('--tax', type=float, default=None,
                        help='【可选】印花税比例，默认0.001（千分之一）')
    parser.add_argument('--position', type=float, default=None,
                        help='【可选】仓位比例，默认0.95（95%%）')

    # 风控参数
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='【可选】止损比例，默认0.05（5%%）')
    parser.add_argument('--stop-profit', type=float, default=None,
                        help='【可选】止盈触发比例，默认0.20（20%%）')
    parser.add_argument('--drawdown', type=float, default=None,
                        help='【可选】从最高点回落止盈比例，默认0.03（3%%）')
    parser.add_argument('--trailing-stop', type=float, default=None,
                        help='【可选】移动止损比例（从最高价回落），默认0=不启用。'
                             '如0.07表示从最高价回撤7%%时卖出')
    parser.add_argument('--trailing-profit', type=float, default=None,
                        help='【可选】移动止盈激活涨幅，默认0.15（15%%）。'
                             '涨幅超过此值后才激活移动止损')

    # 性能参数
    parser.add_argument('--workers', type=int, default=None,
                        help='【可选】并行线程数，默认4。多股票时加速')

    return parser.parse_args()


# ============================================================================
# 主入口
# ============================================================================

def main():
    args = parse_args()

    # 列出所有技术指标
    if args.list_indicators:
        print(f'\nGF 综合指标 — 共 {len(GFSignal.INDICATORS)} 个技术指标:\n')
        # 按分类分组显示
        categories = {
            '价格动量指标（表34）': [
                'DPO', 'ER', 'TII', 'PO', 'MA_DISPLACED', 'T3', 'POS',
                'PAC', 'ADTM', 'ZLMACD', 'TMA', 'TYP', 'KDJD', 'VMA',
                'BIAS', 'WMA_M', 'DDI', 'HMA', 'SROC', 'EXPMA', 'DC',
                'VIDYA', 'QSTICK', 'FB', 'DEMA', 'APZ', 'ASI', 'ARRON',
                'KC', 'MTM', 'CR', 'BOP', 'HULLMA', 'COPP', 'ENV',
                'RSIH', 'HLMA', 'TSI', 'BIAS36', 'UOS', 'DZRSI', 'DZCCI',
                'CMF', 'PPO', 'RWI', 'ATR', 'WAD', 'KST', 'VI',
                'DMA_I', 'MICD', 'PMO', 'RCCD', 'KAMA', 'AWS', 'ARBR',
                'ADXR', 'SMI', 'SI', 'DO', 'DBCD', 'CV',
            ],
            '价格反转指标（表35）': [
                'KDJ', 'RMI', 'SKDJ', 'CCI', 'RSI', 'ROC', 'WR',
                'STC', 'RVI', 'RSIS',
            ],
            '成交量指标（表36）': [
                'MAAMT', 'SROCVOL', 'PVO', 'BIASVOL', 'MACDVOL', 'ROCVOL',
            ],
            '价量指标（表37）': [
                'VWAP', 'FI', 'NVI', 'PVT', 'RSIV', 'AMV', 'VRAMT',
                'WVAD', 'OBV', 'PVI', 'TMF', 'MFI', 'ADOSC', 'VAO', 'VR',
                'KO', 'EMV',
            ],
            '混合指标': ['MACD'],
        }
        for cat, inds in categories.items():
            print(f'  【{cat}】')
            # 每行显示 5 个
            for i in range(0, len(inds), 5):
                row = inds[i:i + 5]
                print(f'    {"  ".join(f"{x:12s}" for x in row)}')
            print()
        print('用法: python run_backtest.py --stocks 000012 --indicator KDJ')
        return

    # 校验必填参数
    if not args.stocks:
        print('错误: 请指定股票代码（--stocks）')
        print('示例: python run_backtest.py --stocks 000012,000014 --indicator KDJ')
        sys.exit(1)

    # 构建配置
    cfg = DEFAULT_CONFIG.copy()

    # 股票和时间
    cfg['stock_codes'] = [s.strip() for s in args.stocks.split(',')]
    if args.start:
        cfg['start_date'] = args.start
    if args.end:
        cfg['end_date'] = args.end

    # 指标名称
    cfg['indicator'] = args.indicator.upper()

    # 指标参数覆盖
    for pname in ['n', 'n1', 'n2', 'n3', 'm']:
        pval = getattr(args, pname, None)
        if pval is not None:
            cfg[f'signal_params_{pname}'] = pval

    # 资金参数覆盖
    if args.money is not None:
        cfg['initial_money_per_stock'] = args.money
    if args.slippage is not None:
        cfg['slippage'] = args.slippage
    if args.commission is not None:
        cfg['commission_rate'] = args.commission
    if args.tax is not None:
        cfg['tax_rate'] = args.tax
    if args.position is not None:
        cfg['position_pct'] = args.position

    # 风控参数覆盖
    if args.stop_loss is not None:
        cfg['stop_loss_pct'] = args.stop_loss
    if args.stop_profit is not None:
        cfg['stop_profit_pct'] = args.stop_profit
    if args.drawdown is not None:
        cfg['drawdown_pct'] = args.drawdown
    if args.trailing_stop is not None:
        cfg['trailing_stop_pct'] = args.trailing_stop
    if args.trailing_profit is not None:
        cfg['trailing_profit_pct'] = args.trailing_profit

    # 并行参数
    if args.workers is not None:
        cfg['max_workers'] = args.workers

    # 构建信号参数
    signal_params = {}
    for pname in ['n', 'n1', 'n2', 'n3', 'm']:
        key = f'signal_params_{pname}'
        if key in cfg:
            signal_params[pname] = cfg[key]

    # 判断是否为多指标组合模式
    combo_indicators = [s.strip().upper() for s in args.indicators.split(',') if s.strip()]
    if len(combo_indicators) >= 2:
        # 多指标组合模式
        strategy = ComboGFSignal(indicators=combo_indicators,
                                 combo_mode=args.combo_mode,
                                 **signal_params)
        tag_indicator = f'COMBO_{"+".join(strategy.indicators)}'
        print(f'  组合策略: {" + ".join(strategy.indicators)} [{args.combo_mode}]')
    else:
        # 单指标模式（原行为）
        cfg['indicator'] = args.indicator.upper()
        signal_params['indicator'] = cfg['indicator']
        strategy = GFSignal(**signal_params)
        tag_indicator = strategy._indicator

    # 创建配置对象
    config = BacktestConfig(
        stock_codes=cfg['stock_codes'],
        start_date=cfg.get('start_date', '2022-01-01'),
        end_date=cfg.get('end_date', ''),
        benchmark_code=cfg.get('benchmark_code', 'sh.000300'),
        initial_money_per_stock=cfg.get('initial_money_per_stock', 10000),
        slippage=cfg.get('slippage', 0.003),
        commission_rate=cfg.get('commission_rate', 0.0005),
        tax_rate=cfg.get('tax_rate', 0.001),
        position_pct=cfg.get('position_pct', 0.95),
        risk_free_rate=cfg.get('risk_free_rate', 0.027),
        stop_loss_pct=cfg.get('stop_loss_pct', 0.05),
        stop_profit_pct=cfg.get('stop_profit_pct', 0.20),
        drawdown_pct=cfg.get('drawdown_pct', 0.03),
        trailing_stop_pct=cfg.get('trailing_stop_pct', 0.0),
        trailing_profit_pct=cfg.get('trailing_profit_pct', 0.15),
        max_workers=cfg.get('max_workers', 4),
        tag=args.tag or f'{tag_indicator}_{cfg["start_date"]}',
    )

    # 执行回测
    engine = BacktestEngine(config)
    engine.register_signal(strategy)
    engine.run()


if __name__ == '__main__':
    main()
