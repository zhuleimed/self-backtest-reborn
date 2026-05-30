# 002_self_backtest_reborn

模块化量化回测框架，基于 GF 指标公式库（97 个技术指标）。

## 项目架构

```
run_backtest.py    ← 回测入口（--stocks + --indicator）
run_compare.py     ← 多指标对比入口
run_optimize.py    ← 参数优化入口
config/
  backtest_config.py  ← 默认配置
core/               ← 回测引擎模块
signals/
  gf.py             ← GF 综合策略入口（97 个指标）
  gf_factors.py     ← 指标计算函数库（143 个函数）
```

## 快速开始

```bash
# 运行回测
python run_backtest.py --stocks 000012 --indicator KDJ

# 多指标对比
python run_compare.py --strategies KDJ,RSI,MACD

# 参数优化
python run_optimize.py --indicator KDJ
```

## 关键文件说明

- `run_backtest.py`: CLI 入口，支持 `--stocks`, `--start`, `--end`, `--indicator`, `--stop-loss` 等参数
- `run_compare.py`: 多指标对比，`--strategies KDJ,MACD`
- `run_optimize.py`: 参数网格优化，`--indicator KDJ --objective sharpe_ratio`
- `config/backtest_config.py`: 预设默认参数，运行前可在此修改
- `signals/gf.py`: 唯一策略类 `GFSignal`，通过 `indicator` 参数选择具体指标
- `core/engine.py`: `BacktestEngine` 5 步流水线：加载→信号→风控→曲线→报告
- `core/risk_manager.py`: 止盈止损（stop_loss/profit/drawdown_pct）+ 涨跌停限制
- Output: `output/YYYYMMDD/HHMM/` 按日期时间分层

## 数据来源

股票日线 CSV 位于 `../data/input/`，来自 baostock 数据下载。
