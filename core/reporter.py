"""
报告生成模块 (Reporter)

职责：
  1. 生成回测结果 CSV 文件
  2. 绘制策略 vs 基准累积收益率对比图
  3. 输出绩效指标汇总
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # 非交互后端，适用于服务器环境

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

from .equity_curve import TradeRecord
from .metrics import BacktestMetrics


class Reporter:
    """回测报告生成器"""

    # 尝试使用中文字体
    # CJK 字体路径（DroidSansFallback 支持中文，matplotlib 可识别）
    _CJK_FONT_PATH = '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'
    _CJK_FONT_NAME = 'Droid Sans Fallback'

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._setup_matplotlib()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def save_trade_records(self,
                           trade_records: List[List[TradeRecord]],
                           stock_codes: List[str],
                           filename: str = '') -> str:
        """
        保存交易记录为 CSV。

        trade_records 与 stock_codes ——对应。
        """
        if not trade_records:
            return ''

        records = []
        for stock_records, code in zip(trade_records, stock_codes):
            for t in stock_records:
                records.append({
                    '股票代码': code,
                    '日期': t.date,
                    '交易类型': t.trade_type,
                    '价格': round(t.price, 2),
                    '数量': t.volume,
                    '手续费': t.commission,
                    '印花税': t.tax,
                    '总成本': round(t.total_cost, 2),
                    '总收入': round(t.total_revenue, 2),
                    '盈亏金额': round(t.profit, 2),
                    '持股天数': t.days_held,
                    '收益率': round(t.return_rate, 4),
                })

        df = pd.DataFrame(records)
        # 按股票代码和日期排序
        df = df.sort_values(['股票代码', '日期'])

        # 累计盈亏
        df['累计盈亏'] = df.groupby('股票代码')['盈亏金额'].cumsum().round(2)

        cols = ['股票代码', '日期', '交易类型', '价格', '数量', '持股天数',
                '手续费', '印花税', '总成本', '总收入', '收益率', '盈亏金额', '累计盈亏']
        df = df[cols]

        filename = filename or f'trade_records_{datetime.now():%Y%m%d_%H%M}.csv'
        path = self._path(filename)
        df.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'  📄 交易记录 → {path}')
        return path

    def save_account_curve(self, account_data: pd.DataFrame,
                           benchmark_data: pd.DataFrame = None,
                           filename: str = '') -> str:
        """保存账户资金曲线 CSV"""
        df = account_data[['date', 'cash', 'stock_value', 'equity',
                           'equity_returns', 'equity_cumulative_returns']].copy()

        if benchmark_data is not None:
            # 在 datetime 类型下做 merge_asof（避免 dtype('O') 错误）
            bench = benchmark_data[['date', 'benchmark_cumulative_returns']].copy()
            merged = pd.merge_asof(
                df.sort_values('date'), bench.sort_values('date'),
                on='date', direction='nearest',
            )
            merged['benchmark_cumulative_returns'] = (
                merged['benchmark_cumulative_returns'].ffill()
            )
            df = merged

        # CSV 输出时转字符串
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        filename = filename or f'account_curve_{datetime.now():%Y%m%d_%H%M}.csv'
        path = self._path(filename)
        df.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'  📄 资金曲线 → {path}')
        return path

    def save_metrics(self, metrics: BacktestMetrics,
                     stock_codes: List[str],
                     start_date: str, end_date: str,
                     filename: str = '') -> str:
        """保存绩效指标 CSV"""
        data = metrics.to_dict()
        data.update({
            '股票池': '|'.join(stock_codes),
            '开始日期': start_date,
            '结束日期': end_date,
        })
        df = pd.DataFrame([data])
        filename = filename or f'metrics_{datetime.now():%Y%m%d_%H%M}.csv'
        path = self._path(filename)
        df.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'  📄 绩效指标 → {path}')
        return path

    def plot_returns(self, account_data: pd.DataFrame,
                     benchmark_data: pd.DataFrame = None,
                     title: str = '策略收益 vs 基准收益',
                     filename: str = '') -> str:
        """
        绘制策略累积收益率 vs 基准累积收益率对比图。

        Returns
        -------
        str
            图片文件路径
        """
        fig, ax = plt.subplots(figsize=(16, 6))

        strategy = account_data['equity_cumulative_returns'] - 1
        ax.plot(strategy, label='策略收益', color='#2E86AB', linewidth=1.5)

        if benchmark_data is not None:
            bench = benchmark_data['benchmark_cumulative_returns'] - 1
            # 对齐长度
            bench_aligned = bench.iloc[:len(strategy)].reset_index(drop=True)
            ax.plot(bench_aligned, label='基准收益', color='#A23B72',
                    linewidth=1.5, linestyle='--')

        # 标注最大回撤区间
        cumulative = account_data['equity_cumulative_returns']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        dd_min_idx = drawdown.idxmin()
        if not np.isnan(dd_min_idx):
            peak_before = cumulative.iloc[:dd_min_idx].idxmax()
            recovery = (cumulative.iloc[dd_min_idx:] >= running_max.iloc[dd_min_idx])
            recovery_idx = recovery[recovery].index.min() if recovery.any() else len(cumulative)
            ax.axvspan(peak_before, min(recovery_idx, len(cumulative) - 1),
                       color='lightblue', alpha=0.2, label='最大回撤区间')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('交易日')
        ax.set_ylabel('累积收益率')
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        ax.legend(fontsize=11)

        plt.tight_layout()
        filename = filename or f'returns_chart_{datetime.now():%Y%m%d_%H%M}.png'
        path = self._path(filename)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'  📊 收益曲线图 → {path}')
        return path

    def print_summary(self, metrics: BacktestMetrics):
        """控制台打印指标摘要"""
        sep = '=' * 50
        print(f'\n{sep}')
        print(f'  回测绩效摘要')
        print(sep)
        data = metrics.to_dict()
        for key in ['总收益率', '年化收益率', '基准收益率', '超额收益',
                     '夏普比率', 'Sortino比率', 'Calmar比率',
                     '最大回撤', '年化波动率', '胜率(日)']:
            print(f'  {key:12s}: {data[key]:>10.4f}')
        print(f'  {"总交易次数":12s}: {data["总交易次数"]}')
        print(f'  {"止损次数":12s}: {data["止损次数"]}')
        print(f'  {"止盈次数":12s}: {data["止盈次数"]}')
        print(f'  {"平均持股天数":12s}: {data["平均持股天数"]}')
        print(sep)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _path(self, filename: str) -> str:
        """输出文件的完整路径"""
        os.makedirs(self.output_dir, exist_ok=True)
        return os.path.join(self.output_dir, filename)

    def _setup_matplotlib(self):
        """配置 Matplotlib 中文字体"""
        plt.rcParams['axes.unicode_minus'] = False
        try:
            # 直接注册系统已有的 DroidSansFallback 字体（支持 CJK）
            fm.fontManager.addfont(self._CJK_FONT_PATH)
            plt.rcParams['font.sans-serif'] = [self._CJK_FONT_NAME]
            plt.rcParams['font.family'] = 'sans-serif'
            return
        except Exception:
            pass
        # 兜底：尝试常用中文字体名称
        for name in ['WenQuanYi Micro Hei', 'SimHei', 'Microsoft YaHei',
                      'Noto Sans CJK SC', 'AR PL UMing CN']:
            try:
                fm.findfont(name, fallback_to_default=False)
                plt.rcParams['font.family'] = name
                return
            except Exception:
                continue
        plt.rcParams['font.family'] = 'DejaVu Sans'
