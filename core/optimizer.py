"""
参数优化网格模块 (ParameterOptimizer)

职责：
  1. 对指定策略的参数进行网格扫描
  2. 支持多目标优化（总收益率、夏普比率、卡玛比率等）
  3. 输出最佳参数组合 + 参数敏感性热力图
"""

import itertools
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

from .engine import BacktestConfig, BacktestEngine
from .metrics import BacktestMetrics
from .signal_engine import BaseSignal


@dataclass
class ParamGridResult:
    """参数网格单次运行结果"""
    params: Dict[str, float]
    metrics: 'BacktestMetrics'


class ParameterOptimizer:
    """参数优化器（网格搜索）"""

    _CJK_FONT_PATH = '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'
    _CJK_FONT_NAME = 'Droid Sans Fallback'

    # 可选的目标函数
    OBJECTIVES = {
        'total_return': lambda m: m.total_return,
        'annualized_return': lambda m: m.annualized_return,
        'sharpe_ratio': lambda m: m.sharpe_ratio,
        'sortino_ratio': lambda m: m.sortino_ratio,
        'calmar_ratio': lambda m: m.calmar_ratio,
        'win_rate': lambda m: m.win_rate,
        'profit_factor': lambda m: m.profit_factor,
    }

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._results: List[ParamGridResult] = []
        self._top_k = 5
        self._setup_matplotlib()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def grid_search(self,
                    signal_class: type,
                    param_grid: Dict[str, List],
                    base_config: BacktestConfig,
                    objective: str = 'sharpe_ratio',
                    top_k: int = 5,
                    maximize: bool = True) -> List[ParamGridResult]:
        """
        网格搜索最佳参数组合。

        Parameters
        ----------
        signal_class : type
            信号策略类（未实例化）
        param_grid : dict
            参数网格，如 {'n': [5, 10, 15], 'fast': [2, 3]}
        base_config : BacktestConfig
            基础回测配置（策略参数之外的部分）
        objective : str
            优化目标，可选:
              total_return, annualized_return, sharpe_ratio,
              sortino_ratio, calmar_ratio, win_rate, profit_factor
        top_k : int
            输出前 K 个最佳组合
        maximize : bool
            True 表示最大化目标，False 表示最小化

        Returns
        -------
        list of ParamGridResult
            按目标值排序的结果列表
        """
        obj_func = self.OBJECTIVES.get(objective)
        if obj_func is None:
            raise ValueError(f'未知目标函数: {objective}，可选: {list(self.OBJECTIVES.keys())}')

        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        total = len(combinations)

        print(f'\n[参数优化] 目标: {objective}, 网格: {total} 组参数')
        print(f'  参数范围: {param_grid}')
        print('-' * 50)

        self._results = []

        for idx, combo in enumerate(combinations, 1):
            params = dict(zip(param_names, combo))
            print(f'  [{idx}/{total}] {params}…', end=' ', flush=True)

            # 创建策略实例
            signal = signal_class(**params)

            # 运行回测
            config = BacktestConfig(
                **{k: v for k, v in base_config.__dict__.items()
                   if k != 'tag'}  # 动态 tag 由 engine 内部处理
            )
            config.tag = f'opt_{objective}_{idx}'

            try:
                engine = BacktestEngine(config)
                engine.register_signal(signal)
                metrics = engine.run()

                self._results.append(ParamGridResult(
                    params=params, metrics=metrics
                ))
                print(f'✓ {objective}={obj_func(metrics):.4f}')
            except Exception as e:
                print(f'✗ {e}')

        if not self._results:
            raise RuntimeError('所有参数组合均回测失败')

        # 排序
        self._results.sort(
            key=lambda r: obj_func(r.metrics),
            reverse=maximize,
        )

        self._top_k = min(top_k, len(self._results))

        # 输出结果
        print(f'\n{"=" * 60}')
        print(f'  🏆 最佳 {self._top_k} 组参数 (目标: {objective})')
        print(f'{"=" * 60}')
        for i, r in enumerate(self._results[:self._top_k], 1):
            obj_val = obj_func(r.metrics)
            print(f'  #{i}: {r.params} → {objective} = {obj_val:.4f}')

        # 保存 & 绘图
        self._save_results(objective, obj_func)
        self._plot_heatmap(objective, obj_func, param_grid)

        return self._results[:self._top_k]

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _save_results(self, objective: str,
                      obj_func: Callable) -> str:
        """保存结果到 CSV"""
        rows = []
        for r in self._results:
            d = r.metrics.to_dict()
            d.update(r.params)
            d['objective'] = objective
            d['objective_value'] = obj_func(r.metrics)
            rows.append(d)

        df = pd.DataFrame(rows)
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        path = os.path.join(self.output_dir, f'optimization_{objective}_{ts}.csv')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'\n  📄 优化结果 → {path}')
        return path

    def _plot_heatmap(self, objective: str,
                      obj_func: Callable,
                      param_grid: Dict[str, List]):
        """
        绘制参数敏感性热力图（仅支持 2 个可变参数时自动生成）。
        """
        if len(param_grid) < 2:
            return

        # 取前两个参数做热力图，其余固定为最佳组合
        param_names = list(param_grid.keys())
        x_name, y_name = param_names[0], param_names[1]

        best_params = self._results[0].params if self._results else {}
        fixed_params = {k: best_params.get(k) for k in param_names[2:]}

        # 构建矩阵
        x_vals = sorted(param_grid[x_name])
        y_vals = sorted(param_grid[y_name])
        matrix = np.full((len(y_vals), len(x_vals)), np.nan)

        for r in self._results:
            x_idx = x_vals.index(r.params[x_name])
            y_idx = y_vals.index(r.params[y_name])
            # 只对固定参数匹配的行填充
            match = all(
                r.params.get(k) == v for k, v in fixed_params.items()
            )
            if match:
                matrix[y_idx, x_idx] = obj_func(r.metrics)

        fig, ax = plt.subplots(figsize=(10, 7))
        im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto',
                       interpolation='nearest')

        ax.set_xticks(range(len(x_vals)))
        ax.set_yticks(range(len(y_vals)))
        ax.set_xticklabels([str(v) for v in x_vals])
        ax.set_yticklabels([str(v) for v in y_vals])
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        ax.set_title(f'参数敏感性 — {objective}（{x_name} × {y_name}）')

        # 标注数值
        for i in range(len(y_vals)):
            for j in range(len(x_vals)):
                val = matrix[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f'{val:.3f}', ha='center', va='center',
                            fontsize=8, color='black' if abs(val) < 0.5 else 'white')

        plt.colorbar(im, label=objective)
        plt.tight_layout()

        ts = datetime.now().strftime('%Y%m%d_%H%M')
        path = os.path.join(self.output_dir,
                            f'optimization_heatmap_{objective}_{ts}.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'  📊 热力图 → {path}')

    def _setup_matplotlib(self):
        plt.rcParams['axes.unicode_minus'] = False
        try:
            if os.path.exists(self._CJK_FONT_PATH):
                fm.fontManager.addfont(self._CJK_FONT_PATH)
                plt.rcParams['font.sans-serif'] = [self._CJK_FONT_NAME]
                plt.rcParams['font.family'] = 'sans-serif'
        except Exception:
            pass
