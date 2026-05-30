# 002_self_backtest_reborn

模块化量化回测框架，基于 **Claude Code 最佳实践**的 Command → Agent → Skill 三层架构设计。

## 设计理念

```
┌─────────────────────────────────────────────────────────┐
│  Command Layer:  /run-backtest (用户交互入口)             │
├─────────────────────────────────────────────────────────┤
│  Agent Layer:    backtest-agent (流程编排)                │
│  Skills:  data-loader → signal-generator → risk-manager  │
│           → equity-calc → report-builder                  │
├─────────────────────────────────────────────────────────┤
│  Core Layer:  模块化 Python 回测引擎                      │
│  DataLoader → SignalEngine → RiskManager → EquityCurve → │
│  Metrics → Reporter                                      │
├─────────────────────────────────────────────────────────┤
│  Signal Layer: 可插拔策略（KAMA、MACD、其他）             │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 查看预置方案
python run_backtest.py --list-plans

# 运行默认回测（KAMA + demo 股票池）
python run_backtest.py

# 使用预置方案
python run_backtest.py --plan kama_demo

# 自定义参数
python run_backtest.py --stocks 000012,000014,000016 \
                       --start 2022-01-01 \
                       --signal KAMA --n 15 --fast 2 --slow 30 \
                       --stop-loss 0.05 --stop-profit 0.20
```

## 目录结构

```
002_self_backtest_reborn/
├── core/                  # 核心引擎模块
│   ├── data_loader.py     # 数据加载
│   ├── signal_engine.py   # 信号引擎 + 基类
│   ├── risk_manager.py    # 风控管理
│   ├── equity_curve.py    # 资金曲线计算
│   ├── metrics.py         # 绩效指标
│   ├── reporter.py        # 报告生成
│   └── engine.py          # 回测引擎编排
├── signals/               # 可插拔信号策略
│   ├── base.py            # (继承自 core.signal_engine.BaseSignal)
│   └── kama.py            # KAMA 策略
├── config/
│   └── backtest_config.py # 预置回测方案
├── .claude/
│   ├── commands/          # /run-backtest 命令
│   ├── agents/            # backtest-agent 定义
│   └── skills/            # 5 个独立技能
├── run_backtest.py        # 入口脚本
└── output/                # 回测结果输出
```

## 添加新策略

1. 在 `signals/` 下创建策略文件，继承 `BaseSignal`：
```python
from core.signal_engine import BaseSignal

class MyStrategy(BaseSignal):
    name = 'MY'
    params = {'p1': 10}
    def compute(self, data):
        # ... 生成 my_signal 列
        return data
```

2. 在 `run_backtest.py` 的 `SIGNAL_FACTORY` 中注册：
```python
SIGNAL_FACTORY['MY'] = MyStrategy
```

3. 运行：
```bash
python run_backtest.py --stocks 000012 --signal MY
```

## 数据来源

股票日线 CSV 文件位于 `../data/input/`，来自 baostock 数据下载。
