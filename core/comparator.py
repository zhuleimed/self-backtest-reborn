"""
多策略对比模块 (StrategyComparator)

职责：
  1. 对同一组股票/时间范围，用多个策略分别跑回测
  2. 横向对比各策略的绩效指标
  3. 生成对比报告（CSV + 图表）
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

from .engine import BacktestConfig, BacktestEngine
from .metrics import BacktestMetrics
from .signal_engine import BaseSignal
from .reporter import Reporter


@dataclass
class ComparisonResult:
    """单策略对比结果"""
    name: str
    metrics: BacktestMetrics
    account_curve: pd.DataFrame
    trade_count: int


class StrategyComparator:
    """多策略对比器"""

    # 中文字体配置（与 reporter.py 保持一致）
    _CJK_FONTS = [
        ('/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf', 'Droid Sans Fallback'),
        ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Noto Sans CJK SC'),
    ]
    _PATH_CACHE = '~/.cache/matplotlib'

    def __init__(self, output_dir: str):
        self._base_output_dir = output_dir
        self.output_dir = output_dir
        self._results: List[ComparisonResult] = []
        self._setup_matplotlib()

    def _ensure_dated_dir(self):
        """创建日期/时间分层输出目录并更新 self.output_dir"""
        now = datetime.now()
        self.output_dir = os.path.join(
            self._base_output_dir,
            now.strftime('%Y%m%d'),
            now.strftime('%H%M'),
        )
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def add_strategy(self, name: str, signal: BaseSignal,
                     config: BacktestConfig) -> 'StrategyComparator':
        """
        添加一个策略参与对比。

        Parameters
        ----------
        name : str
            策略显示名称
        signal : BaseSignal
            信号策略实例
        config : BacktestConfig
            回测配置（股票池、时间等会共享）
        """
        engine = BacktestEngine(config)
        engine.register_signal(signal)
        tag = f'compare_{name}'
        config.tag = tag

        print(f'\n[对比] 运行策略 "{name}"…')
        metrics = engine.run()

        # 收集交易记录数
        trade_count = sum(
            len(r['trade_records']) for r in engine._stock_results
        )

        self._results.append(ComparisonResult(
            name=name,
            metrics=metrics,
            account_curve=engine._account_data.copy(),
            trade_count=trade_count,
        ))
        return self

    def compare(self, strategies: List[Tuple[str, BaseSignal]],
                config: BacktestConfig) -> 'StrategyComparator':
        """
        批量对比多个策略。

        Parameters
        ----------
        strategies : list of (name, signal)
        config : BacktestConfig
        """
        for name, signal in strategies:
            self.add_strategy(name, signal, config)
        return self

    def report(self, filename: str = '') -> str:
        """
        生成对比报告：
          1. 对比指标 CSV
          2. 收益率曲线叠加图
        """
        if not self._results:
            raise RuntimeError('没有对比结果，请先调用 add_strategy 或 compare')

        # 创建日期/时间分层输出目录
        self._ensure_dated_dir()
        ts = datetime.now().strftime('%Y%m%d_%H%M')

        # ---- 对比 CSV ----
        rows = []
        for r in self._results:
            d = r.metrics.to_dict()
            d['策略名称'] = r.name
            d['交易次数'] = r.trade_count
            rows.append(d)

        df = pd.DataFrame(rows)
        cols = ['策略名称'] + [c for c in df.columns if c != '策略名称']
        df = df[cols]

        csv_path = (filename or
                    os.path.join(self.output_dir, f'comparison_{ts}.csv'))
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f'\n  📄 对比报告 → {csv_path}')

        # ---- 收益率曲线叠加图 ----
        self._plot_comparison(ts)

        return csv_path

    # ------------------------------------------------------------------
    # 绘图
    # ------------------------------------------------------------------

    def _plot_comparison(self, ts: str):
        """绘制多策略收益率曲线对比"""
        fig, ax = plt.subplots(figsize=(16, 7))

        colors = ['#2E86AB', '#A23B72', '#F18F01', '#5D576B',
                  '#4ECDC4', '#FF6B6B', '#45B7D1', '#96CEB4']
        markers = ['-', '--', '-.', ':', (0, (3, 1, 1, 1)),
                   (0, (5, 2)), (0, (1, 1)), (0, (3, 1, 1, 1, 1, 1))]

        for idx, result in enumerate(self._results):
            curve = result.account_curve['equity_cumulative_returns'] - 1
            color = colors[idx % len(colors)]
            style = markers[idx % len(markers)]
            ax.plot(curve, label=result.name, color=color,
                    linestyle=style, linewidth=1.8, alpha=0.85)

        ax.set_title('多策略累积收益率对比', fontsize=14, fontweight='bold')
        ax.set_xlabel('交易日')
        ax.set_ylabel('累积收益率')
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        ax.legend(fontsize=10, loc='upper left',
                  bbox_to_anchor=(1.01, 1), borderaxespad=0)

        plt.tight_layout()
        path = os.path.join(self.output_dir, f'comparison_{ts}.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'  📊 对比曲线图 → {path}')

    def _setup_matplotlib(self):
        """配置 Matplotlib 中文字体（与 reporter.py 一致的方案）"""
        # 清除字体缓存
        cache_dir = os.path.expanduser(self._PATH_CACHE)
        if os.path.isdir(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.startswith('fontlist'):
                    try:
                        os.remove(os.path.join(cache_dir, fname))
                    except OSError:
                        pass
        fm._load_fontmanager(try_read_cache=False)

        # 注册字体
        registered = []
        for path, name in self._CJK_FONTS:
            try:
                if os.path.exists(path):
                    fm.fontManager.addfont(path)
                    registered.append(name)
            except Exception:
                pass

        plt.rcParams['font.sans-serif'] = registered + ['DejaVu Sans']
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False

    @property
    def results(self) -> List[ComparisonResult]:
        return self._results
