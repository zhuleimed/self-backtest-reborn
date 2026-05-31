"""
多策略对比模块 (StrategyComparator)

职责：
  1. 对同一组股票/时间范围，用多个策略分别跑回测
  2. 横向对比各策略的绩效指标
  3. 生成对比报告（CSV + 图表）
"""

import copy
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

from .log_utils import get_logger

logger = get_logger(__name__)

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
        ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Noto Sans CJK JP'),
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
        try:
            metrics = engine.run()
        except Exception as e:
            print(f'  ⚠ 跳过 {name}: {e}')
            return self

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
                config: BacktestConfig,
                max_workers: int = 1) -> 'StrategyComparator':
        """
        批量对比多个策略。

        Parameters
        ----------
        strategies : list of (str, BaseSignal)
            策略列表
        config : BacktestConfig
            共享回测配置
        max_workers : int
            并行工作线程数。1=串行（默认）。
            全量对比（--strategies ALL）时建议设 4~8 以加速。
        """
        if max_workers <= 1 or len(strategies) <= 1:
            # 串行模式（原行为）
            for name, signal in strategies:
                self.add_strategy(name, signal, config)
            return self

        # 并行模式
        print(f'\n[并行对比] 启动 {min(max_workers, len(strategies))} 个线程 '
              f'处理 {len(strategies)} 个策略…')

        def run_one(name, signal, cfg):
            """单线程运行一个策略回测"""
            print(f'\n[对比] 运行策略 "{name}"…')
            cfg.tag = f'compare_{name}'
            engine = BacktestEngine(cfg)
            engine.register_signal(signal)
            try:
                metrics = engine.run()
            except Exception as e:
                print(f'  ⚠ 跳过 {name}: {e}')
                return None
            return ComparisonResult(
                name=name,
                metrics=metrics,
                account_curve=engine._account_data.copy(),
                trade_count=sum(
                    len(r['trade_records']) for r in engine._stock_results
                ),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_one, name, signal, copy.deepcopy(config))
                for name, signal in strategies
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    self._results.append(result)

        print(f'\n[并行对比] 完成: {len(self._results)}/{len(strategies)} 个策略成功')
        return self

    def report(self, filename: str = '', top_n: int = 8) -> str:
        """
        生成对比报告：
          1. 对比指标 CSV
          2. 收益率曲线叠加图

        Parameters
        ----------
        filename : str
            自定义 CSV 文件名
        top_n : int
            图表中显示 Top N 个最佳策略（按总收益率排序）。0=全部显示。
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

        # 按总收益率降序排列
        df = df.sort_values('总收益率', ascending=False).reset_index(drop=True)
        df = df[cols]

        csv_path = (filename or
                    os.path.join(self.output_dir, f'comparison_{ts}.csv'))
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f'\n  📄 对比报告 → {csv_path}')

        # 打印 Top-N 排行榜
        print(f'\n  🏆 收益率 Top {min(top_n, len(df))}:')
        for i, row in df.head(top_n).iterrows():
            print(f'    #{i+1:2d}  {row["策略名称"]:18s}  '
                  f'收益率={row["总收益率"]:.2%}  '
                  f'夏普={row["夏普比率"]:.2f}  '
                  f'回撤={row["最大回撤"]:.2%}')

        # ---- 收益率曲线叠加图（仅 Top-N）----
        if top_n > 0 and len(self._results) > top_n:
            # 按总收益率排序后取前 top_n 个
            sorted_results = sorted(
                self._results,
                key=lambda r: r.metrics.total_return,
                reverse=True,
            )
            plot_results = sorted_results[:top_n]
        else:
            plot_results = self._results

        self._plot_comparison(ts, plot_results)

        return csv_path

    # ------------------------------------------------------------------
    # 绘图
    # ------------------------------------------------------------------

    def _plot_comparison(self, ts: str, plot_results: list = None):
        """绘制多策略对比图（收益率曲线 + 雷达图）"""
        results = plot_results if plot_results is not None else self._results
        n_strategies = len(results)
        if n_strategies == 0:
            return

        colors = ['#2E86AB', '#A23B72', '#F18F01', '#5D576B',
                  '#4ECDC4', '#FF6B6B', '#45B7D1', '#96CEB4']
        markers = ['-', '--', '-.', ':', (0, (3, 1, 1, 1)),
                   (0, (5, 2)), (0, (1, 1)), (0, (3, 1, 1, 1, 1, 1))]

        if n_strategies <= 9:
            # ---- 双图布局：曲线 + 雷达 ----
            fig = plt.figure(figsize=(20, 8))

            ax1 = fig.add_subplot(1, 2, 1)
            for idx, result in enumerate(results):
                curve = result.account_curve['equity_cumulative_returns'] - 1
                color = colors[idx % len(colors)]
                style = markers[idx % len(markers)]
                ax1.plot(curve, label=result.name, color=color,
                         linestyle=style, linewidth=1.8, alpha=0.85)
            ax1.set_title('多策略累积收益率对比', fontsize=14, fontweight='bold')
            ax1.set_xlabel('交易日')
            ax1.set_ylabel('累积收益率')
            ax1.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
            ax1.grid(axis='y', linestyle='--', alpha=0.4)
            ax1.legend(fontsize=8, loc='upper left',
                       bbox_to_anchor=(1.01, 1), borderaxespad=0)

            # 雷达图
            ax2 = fig.add_subplot(1, 2, 2, projection='polar')
            radar_metrics = ['sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
                             'win_rate', 'profit_factor']
            radar_labels = ['夏普', 'Sortino', 'Calmar', '胜率', '盈亏比']

            raw_data = []
            for result in results:
                d = result.metrics.to_dict()
                raw_data.append([d.get(m, 0) for m in radar_metrics])

            raw_arr = np.array(raw_data)
            norms = np.nanmax(np.abs(raw_arr), axis=0)
            norms = np.where(norms > 0, norms, 1)
            norm_data = raw_arr / norms

            angles = np.linspace(0, 2 * np.pi, len(radar_labels), endpoint=False).tolist()
            angles += angles[:1]

            for idx, result in enumerate(results):
                values = norm_data[idx].tolist() + norm_data[idx][:1].tolist()
                ax2.plot(angles, values, color=colors[idx % len(colors)],
                         linewidth=1.5, label=result.name, marker='o', markersize=4)
                ax2.fill(angles, values, alpha=0.1, color=colors[idx % len(colors)])

            ax2.set_xticks(angles[:-1])
            ax2.set_xticklabels(radar_labels, fontsize=11)
            ax2.set_title('多策略绩效雷达图', fontsize=14, fontweight='bold', pad=20)
            ax2.set_yticklabels([])
            plt.tight_layout()
            path = os.path.join(self.output_dir, f'comparison_{ts}.png')
            fig.savefig(path, dpi=150, bbox_inches='tight')
            plt.close(fig)
        else:
            # ---- 单曲线图 ----
            fig, ax = plt.subplots(figsize=(16, 7))
            for idx, result in enumerate(results):
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
            ax.legend(fontsize=9, loc='upper left',
                      bbox_to_anchor=(1.01, 1), borderaxespad=0)
            plt.tight_layout()
            path = os.path.join(self.output_dir, f'comparison_{ts}.png')
            fig.savefig(path, dpi=150, bbox_inches='tight')
            plt.close(fig)

        logger.info(f'对比图表 → {path}')

    def _setup_matplotlib(self):
        """配置 Matplotlib 中文字体（与 reporter.py 一致的方案）"""
        cache_dir = os.path.expanduser(self._PATH_CACHE)
        if os.path.isdir(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.startswith('fontlist'):
                    try:
                        os.remove(os.path.join(cache_dir, fname))
                    except OSError:
                        pass
        fm._load_fontmanager(try_read_cache=False)

        for path, name in self._CJK_FONTS:
            try:
                if os.path.exists(path):
                    fm.fontManager.addfont(path)
            except Exception:
                pass

        plt.rcParams['font.family'] = 'Noto Sans CJK JP'
        plt.rcParams['axes.unicode_minus'] = False

    @property
    def results(self) -> List[ComparisonResult]:
        return self._results
