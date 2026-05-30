"""
回测引擎主模块 (BacktestEngine)

职责：
  作为回测流程的总编排器，将以下模块串联为完整的流水线：
    DataLoader → SignalEngine → RiskManager → EquityCurveCalculator → MetricsCalculator → Reporter

  支持两种运行模式：
    1. run() — 完整回测流程（从数据到报告）
    2. run_pipeline() — 逐步执行，每一步可独立调用
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from .data_loader import DataLoader
from .signal_engine import SignalEngine, BaseSignal
from .risk_manager import RiskManager
from .equity_curve import BacktestParams, EquityCurveCalculator, TradeRecord
from .metrics import BacktestMetrics, MetricsCalculator
from .reporter import Reporter


@dataclass
class BacktestConfig:
    """回测完整配置"""
    # 股票与时间
    stock_codes: List[str] = field(default_factory=list)
    start_date: str = ''
    end_date: str = ''
    benchmark_code: str = 'sh.000300'  # 沪深300

    # 资金与交易参数
    initial_money_per_stock: float = 10_000.0
    slippage: float = 0.003
    commission_rate: float = 0.0005
    tax_rate: float = 0.001
    position_pct: float = 0.95
    risk_free_rate: float = 0.027

    # 风控参数
    stop_loss_pct: float = 0.05
    stop_profit_pct: float = 0.20
    drawdown_pct: float = 0.03

    # 路径
    data_dir: Optional[str] = None  # 股票 CSV 目录（None 则自动获取）
    output_dir: str = ''

    # 报告
    tag: str = ''      # 报告文件前缀

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 'output'
            )
        if self.start_date and isinstance(self.start_date, str):
            self.start_date = self.start_date


class BacktestEngine:
    """回测引擎——流水线总编排器"""

    def __init__(self, config: BacktestConfig):
        self.config = config

        # 子模块
        self.data_loader = DataLoader(config.data_dir)
        self.signal_engine = SignalEngine()
        self.risk_manager = RiskManager()
        trade_params = BacktestParams(
            initial_money=config.initial_money_per_stock,
            slippage=config.slippage,
            commission_rate=config.commission_rate,
            tax_rate=config.tax_rate,
            position_pct=config.position_pct,
        )
        self.equity_calculator = EquityCurveCalculator(trade_params)
        self.metrics_calculator = MetricsCalculator(config.risk_free_rate)
        self.reporter = Reporter(config.output_dir)

        # 流水线中间结果缓存
        self._stock_datas: Dict[str, pd.DataFrame] = {}
        self._stock_results: List[Dict] = []
        self._benchmark_data: Optional[pd.DataFrame] = None
        self._account_data: Optional[pd.DataFrame] = None
        self._metrics: Optional[BacktestMetrics] = None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def register_signal(self, strategy: BaseSignal,
                         weight: float = 1.0) -> 'BacktestEngine':
        """注册信号策略"""
        self.signal_engine.register(strategy, weight)
        return self

    @property
    def signal_name(self) -> str:
        """当前注册的策略名称（用于列名）"""
        if self.signal_engine.registered:
            return self.signal_engine.registered[0].name
        return 'strategy'

    def run(self) -> BacktestMetrics:
        """
        执行完整回测流水线：
          数据加载 → 信号生成 → 风控 → 资金曲线 → 绩效指标 → 报告

        输出目录层级：
          output/YYYYMMDD/HHMM/xxx_trade_records.csv
                ↕日期目录  ↕时间目录  ↕文件
        """
        cfg = self.config
        tag = cfg.tag or self.signal_name

        # 生成日期和时间字符串，创建分层输出目录
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H%M')
        ts = f'{date_str}_{time_str}'
        output_subdir = os.path.join(cfg.output_dir, date_str, time_str)
        os.makedirs(output_subdir, exist_ok=True)
        self.reporter.output_dir = output_subdir

        print(f'[回测引擎] 开始回测: {tag}')
        print(f'  股票池: {len(cfg.stock_codes)} 只')
        print(f'  时间:   {cfg.start_date} → {cfg.end_date or "最近"}')
        print(f'  策略:   {self.signal_name}')
        print(f'  输出:   {output_subdir}')
        print('-' * 50)

        # ---- Step 1: 数据加载 ----
        print('[1/5] 加载数据…')
        self._load_stock_data()
        self._load_benchmark_data()
        print(f'  ✓ 加载 {len(self._stock_datas)} 只股票, 1 个基准指数')

        # ---- Step 2: 信号生成 ----
        print('[2/5] 生成交易信号…')
        self._generate_signals()
        print(f'  ✓ 信号策略: {self.signal_name}')

        # ---- Step 3: 风控 ----
        print('[3/5] 施加风控规则…')
        self._apply_risk_controls()

        # ---- Step 4: 资金曲线 ----
        print('[4/5] 计算资金曲线…')
        self._calculate_equity_curves()

        # ---- Step 5: 绩效与报告 ----
        print('[5/5] 计算绩效 & 生成报告…')
        self._compute_metrics()
        self._generate_reports(tag, ts)

        self.reporter.print_summary(self._metrics)
        print(f'[回测引擎] 回测完成 ✓')
        return self._metrics

    # ------------------------------------------------------------------
    # 流水线步骤（可独立调用）
    # ------------------------------------------------------------------

    def run_pipeline(self, steps: List[str] = None) -> dict:
        """
        逐步执行流水线，steps 可选子集：
          ['load', 'signal', 'risk', 'equity', 'report']

        Returns
        -------
        dict
            各步骤产物的引用
        """
        pipeline = {
            'load':   (self._load_stock_data, self._load_benchmark_data),
            'signal': (self._generate_signals,),
            'risk':   (self._apply_risk_controls,),
            'equity': (self._calculate_equity_curves,),
            'report': (self._compute_metrics, self._generate_reports),
        }
        if steps is None:
            steps = list(pipeline.keys())

        for step in steps:
            for func in pipeline.get(step, []):
                func()

        return {
            'stock_datas': self._stock_datas,
            'benchmark': self._benchmark_data,
            'stock_results': self._stock_results,
            'account_data': self._account_data,
            'metrics': self._metrics,
        }

    # ------------------------------------------------------------------
    # 内部步骤实现
    # ------------------------------------------------------------------

    def _load_stock_data(self):
        cfg = self.config
        self._stock_datas = self.data_loader.load_stock_batch(
            cfg.stock_codes, cfg.start_date, cfg.end_date, min_days=240,
            on_error='skip',
        )

    def _load_benchmark_data(self):
        cfg = self.config
        self._benchmark_data = self.data_loader.load_benchmark(
            cfg.benchmark_code, cfg.start_date, cfg.end_date,
        )

    def _generate_signals(self):
        for code, df in self._stock_datas.items():
            self._stock_datas[code] = self.signal_engine.generate(df)

    def _apply_risk_controls(self):
        cfg = self.config
        for code, df in self._stock_datas.items():
            # 涨跌停限制
            df = self.risk_manager.apply_limit_up_down(df)
            # 止盈止损
            df = self.risk_manager.apply_stop_strategy(
                df, self.signal_name,
                stop_loss_pct=cfg.stop_loss_pct,
                stop_profit_pct=cfg.stop_profit_pct,
                drawdown_pct=cfg.drawdown_pct,
            )
            # 修正：如果 stop_signal 为卖出信号(-3)且已有卖出，将 pos 置 0
            for i in range(1, len(df)):
                sig_col = f'{self.signal_name}_signal'
                if df.at[i, sig_col] == -1 and df.at[i, 'stop_signal'] in [-1, -2, -3]:
                    df.at[i, 'pos'] = 0
            df['pos'] = df['pos'].ffill().fillna(0)
            self._stock_datas[code] = df

    def _calculate_equity_curves(self):
        self._stock_results = []
        for code, df in self._stock_datas.items():
            result = self.equity_calculator.compute_single(df)
            self._stock_results.append(result)

        self._account_data = self.equity_calculator.compute_account(
            self._stock_results
        )

    def _compute_metrics(self):
        cfg = self.config
        # 收集交易记录
        all_trade_records = [
            r['trade_records'] for r in self._stock_results
        ]

        benchmark_ret = None
        if self._benchmark_data is not None:
            bench = self._benchmark_data['benchmark_cumulative_returns']
            benchmark_ret = bench.iloc[-1] - 1 if len(bench) > 0 else None

        self._metrics = self.metrics_calculator.compute(
            self._account_data,
            initial_money=cfg.initial_money_per_stock * len(cfg.stock_codes),
            trade_records=all_trade_records,
            benchmark_return=benchmark_ret,
        )

    def _generate_reports(self, tag: str = '', ts: str = ''):
        cfg = self.config
        # 日期时间已由目录层级体现（output/YYYYMMDD/HHMM/），
        # 文件名只需保留策略标记便于区分即可
        prefix = tag or 'backtest'

        # 交易记录
        all_records = [r['trade_records'] for r in self._stock_results]
        active_codes = [
            code for code in cfg.stock_codes if code in self._stock_datas
        ]
        self.reporter.save_trade_records(
            all_records, active_codes,
            filename=f'{prefix}_trade_records.csv',
        )

        # 资金曲线
        self.reporter.save_account_curve(
            self._account_data, self._benchmark_data,
            filename=f'{prefix}_account_curve.csv',
        )

        # 绩效指标
        end_date_str = str(self._account_data['date'].iloc[-1].date())
        self.reporter.save_metrics(
            self._metrics, cfg.stock_codes, cfg.start_date, end_date_str,
            filename=f'{prefix}_metrics.csv',
        )

        # 图表
        codes_str = '-'.join(active_codes[:5])
        if len(active_codes) > 5:
            codes_str += f'-etc{len(active_codes)-5}'
        title = f'{tag} | {codes_str} | {cfg.start_date}→{end_date_str}'
        self.reporter.plot_returns(
            self._account_data, self._benchmark_data,
            title=title,
            filename=f'{prefix}_returns.png',
        )
