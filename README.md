# 📈 模块化量化回测框架

> **002_self_backtest_reborn** — 基于 Claude Code 最佳实践架构设计，支持可插拔策略、多策略对比、参数网格优化

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![GitHub](https://img.shields.io/badge/GitHub-self--backtest--reborn-green)](https://github.com/zhuleimed/self-backtest-reborn)

---

## 📑 目录

- [为什么要有这个框架？](#-为什么要有这个框架)
- [一分钟快速上手](#-一分钟快速上手)
- [项目架构（三层设计）](#-项目架构三层设计)
- [项目文件结构](#-项目文件结构)
- [详细用法指南](#-详细用法指南)
  - [1. 运行回测](#1-运行回测)
  - [2. 多策略对比](#2-多策略对比)
  - [3. 参数优化](#3-参数优化)
  - [4. 添加新策略](#4-添加新策略)
- [所有命令速查表](#-所有命令速查表)
- [各模块详解](#-各模块详解)
- [常见问题](#-常见问题)

---

## 💡 为什么要有这个框架？

### 原来写回测是什么样？

```python
# 传统的回测代码（单体文件，1000+行）
def main():
    # 数据加载、信号计算、风控、资金曲线、绘图
    # 全部写在一个函数里……
    # 改一个参数要找半天
    # 加一个新策略要复制整个文件
```

**问题**：代码耦合严重、难以扩展、每次修改都心惊胆战。

### 这个框架做了什么？

把回测拆解成 **6 个独立模块**，像搭积木一样组装：

```
数据加载 → 信号生成 → 风控 → 资金曲线 → 指标计算 → 报告输出
   │          │         │        │         │         │
 独立模块    独立模块   独立模块  独立模块   独立模块   独立模块
```

**好处**：
- ✅ 加新策略 = 写一个类，一行代码注册
- ✅ 改参数 = 改配置文件，不动代码
- ✅ 对比策略 = 一行命令
- ✅ 找最佳参数 = 一行命令

---

## ⚡ 一分钟快速上手

```bash
# 1. 进到项目目录
cd /public/home/hpc/zhulei/superman/quant/code/002_self_backtest_reborn

# 2. 查看有哪些预置回测方案
python run_backtest.py --list-plans

# 3. 运行一个回测（KAMA策略 + 7只demo股票）
python run_backtest.py --plan kama_demo

# 4. 看结果
ls output/    # CSV报告 + PNG图表都在这里
```

---

## 🏗 项目架构（三层设计）

这个框架按照 **Claude Code 最佳实践** 的分层思想设计：

```
┌──────────────────────────────────────────────────────────────────┐
│  🎯 命令层 (Command)                                              │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  run_backtest.py    ← 你直接运行这个脚本                        │ │
│  │  run_compare.py     ← 多策略对比                               │ │
│  │  run_optimize.py    ← 参数优化                                 │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  你只需要在终端敲命令，其他交给下面两层                              │
├──────────────────────────────────────────────────────────────────┤
│  ⚙️ 核心引擎层 (Core)                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ 数据加载  │→│ 信号生成  │→│  风控    │→│ 资金曲线  │→│ 报告   │ │
│  │DataLoader│ │SigEngine │ │RiskMgr  │ │EquityCrv│ │Reporter│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│  每个模块做一件事，互不干扰                                        │
├──────────────────────────────────────────────────────────────────┤
│  📦 策略层 (Signals)                                              │
│  ┌──────────┬────────────┬────────┬───────────┬────────────┐    │
│  │  KAMA   │ MACD_CDTD  │  ARBR  │BOLL_DKBL  │ BOLL_TDCS  │    │
│  └──────────┴────────────┴────────┴───────────┴────────────┘    │
│  每个策略就是一个类，你可以随便加                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 核心思想：一个模块只做一件事

| 模块 | 它只负责 | 不负责 |
|------|---------|-------|
| `DataLoader` | 读CSV、清洗数据 | 算指标、画图 |
| `SignalEngine` | 生成买卖信号 | 计算收益、控风险 |
| `RiskManager` | 止盈止损、涨跌停 | 算收益率 |
| `EquityCurveCalculator` | 算资金曲线 | 选股票 |
| `MetricsCalculator` | 算绩效指标 | 画图 |
| `Reporter` | 保存CSV、画图 | 做交易决策 |

这样设计的好处：**你想改任何一部分，都不影响其他部分。**

---

## 📁 项目文件结构

```
002_self_backtest_reborn/           ← 项目根目录
│
├── run_backtest.py                 ← 🚀 主入口：运行回测
├── run_compare.py                  ← 🚀 多策略对比入口
├── run_optimize.py                 ← 🚀 参数优化入口
├── CLAUDE.md                       ← 项目说明（给Claude看的）
├── README.md                       ← 本指南（给你看的）
├── .gitignore                      ← Git忽略规则
│
├── config/                         ← 📋 配置中心
│   └── backtest_config.py          ←   预置方案、股票池、参数都在这里
│
├── core/                           ← ⚙️ 核心引擎（7个模块）
│   ├── engine.py                   ←   回测引擎总编排器
│   ├── data_loader.py              ←   数据加载
│   ├── signal_engine.py            ←   信号生成引擎 + 策略基类
│   ├── risk_manager.py             ←   风控（止盈止损、涨跌停）
│   ├── equity_curve.py             ←   资金曲线计算
│   ├── metrics.py                  ←   绩效指标
│   ├── reporter.py                 ←   报告输出
│   ├── comparator.py               ←   多策略对比
│   └── optimizer.py                ←   参数优化
│
├── signals/                        ← 📦 策略库（每个策略一个文件）
│   ├── kama.py                     ←   KAMA 自适应均线策略
│   ├── macd_cdtd.py                ←   MACD 顶底背离策略
│   ├── arbr.py                     ←   ARBR 情绪指标策略
│   ├── boll_dkbl.py                ←   布林带带宽收口策略
│   ├── boll_tdcs.py                ←   布林带参数调优策略
│   ├── gf.py                       ←   🆕 GF 综合指标（97个技术指标统一入口）
│   └── gf_factors.py               ←   🆕 GF 指标计算库（143个函数）
│
├── .claude/                        ← 🤖 Claude Code 配置（不需要你管）
│
└── output/                         ← 📊 回测输出目录（自动生成）
    ├── 20250530/                   ← 日期目录（运行回测的日期）
    │   └── 1719/                   ← 时间目录（24小时制，精确到分钟）
    │       ├── KAMA_trade_records.csv  ← 交易明细
    │       ├── KAMA_account_curve.csv  ← 资金曲线
    │       ├── KAMA_metrics.csv        ← 绩效指标
    │       └── KAMA_returns.png        ← 收益曲线图
    ├── 20250531/                   ← 明天再跑就自动新建目录
    │   └── 0902/
    │       └── ...
    └── ...
```

---

## 📖 详细用法指南

---

### 1. 运行回测

#### 1.1 查看有哪些预置方案

```bash
python run_backtest.py --list-plans

# 输出示例：
#   预置回测方案:
#   ==================================================
#   kama_demo            | KAMA | 7 只 | 2022-01-01
#   kama_hs300           | KAMA | 20 只 | 2020-01-01
#   kama_tight_stop      | KAMA | 7 只 | 2022-01-01
#   boll_dkbl_demo       | BOLL_DKBL | 7 只 | 2022-01-01
#   boll_tdcs_demo       | BOLL_TDCS | 7 只 | 2022-01-01
#
#   🆕 GF 系列没有预置方案，使用方式见下方 1.7
```

每个方案包含：
- **策略**（如 KAMA、BOLL_DKBL）
- **股票池**（几只股票）
- **时间范围**

#### 1.2 使用预置方案

```bash
# 最简单的运行方式
python run_backtest.py --plan kama_demo

# 或者用BOLL策略
python run_backtest.py --plan boll_dkbl_demo
```

#### 1.3 自定义回测参数

```bash
# 自己指定股票、时间、策略
python run_backtest.py \
    --stocks 000012,000014,000016 \    # 股票代码，逗号分隔
    --start 2022-01-01 \                # 开始日期
    --end 2024-12-31 \                  # 结束日期（不填则到最新）
    --signal KAMA \                     # 策略名称（见 --list-plans）
    --tag my_first_backtest             # 你的标记（用于输出文件名）
```

#### 1.4 调整策略参数

```bash
# KAMA 策略有3个参数：n（周期）, fast（快线）, slow（慢线）
python run_backtest.py \
    --stocks 000012 \
    --start 2022-01-01 \
    --signal KAMA \
    --n 15 \          # 默认10，改大更平滑
    --fast 3 \        # 默认2
    --slow 40         # 默认30
```

#### 1.5 调整风控参数

```bash
# 止盈止损可以自己设
python run_backtest.py \
    --stocks 000012 \
    --signal KAMA \
    --stop-loss 0.03 \      # 3% 止损（默认5%）
    --stop-profit 0.15 \    # 15% 止盈（默认20%）
    --drawdown 0.02         # 2% 回落止盈（默认3%）
```

#### 1.6 调整交易成本

```bash
python run_backtest.py \
    --stocks 000012 \
    --money 50000 \        # 每只股票初始资金（默认10000）
    --slippage 0.001 \     # 滑点0.1%（默认0.3%）
    --commission 0.0003 \  # 佣金万分之三（默认万分之五）
    --tax 0.0005           # 印花税万分之五（默认千分之一）
```

#### 1.7 🆕 使用 GF 综合指标（97个技术指标）

框架集成了 **GF 指标公式库**（移植自 `002_self_backtest/GF_factors.py` + `GF_buy_sell_signal.py`），
包含 **97 个技术指标**的统一入口。通过 `--indicator` 参数选择具体指标：

```bash
# 使用 KDJ 指标回测
python run_backtest.py --signal GF --stocks 000012 --indicator KDJ

# 使用 MACD 指标回测
python run_backtest.py --signal GF --stocks 000012 --indicator MACD

# 使用 RSI 指标 + 自定义周期
python run_backtest.py --signal GF --stocks 000012 --indicator RSI --n 14
```

**常用 GF 指标速查表：**

| 分类 | 指标名 | 说明 |
|------|--------|------|
| 价格动量 | KDJ | 随机指标 |
| 价格动量 | MACD | 指数平滑异同平均 |
| 价格动量 | RSI | 相对强弱指数 |
| 价格动量 | CCI | 商品通道指数 |
| 价格动量 | WR | 威廉指标 |
| 价格动量 | BIAS | 乖离率 |
| 成交量 | OBV | 能量潮 |
| 成交量 | MFI | 资金流量指数 |
| 价量 | VWAP | 成交量加权平均价 |
| 价量 | VR | 成交量变异率 |

> 💡 **小提示**：GF 策略也可以加入多策略对比：
> `python run_compare.py --strategies KAMA,GF-KDJ --stocks 000012`

#### 回测完成后你会看到什么？

```
[回测引擎] 开始回测: KAMA_2025-05-30
  股票池: 2 只
  时间:   2024-06-01 → 2024-12-31
  策略:   KAMA
  输出:   output/20250530/1719/
--------------------------------------------------
[1/5] 加载数据…
  ✓ 加载 2 只股票, 1 个基准指数
[2/5] 生成交易信号…
  ✓ 信号策略: KAMA
[3/5] 施加风控规则…
[4/5] 计算资金曲线…
[5/5] 计算绩效 & 生成报告…
  📄 交易记录 → output/20250530/1719/KAMA_trade_records.csv
  📄 资金曲线 → output/20250530/1719/KAMA_account_curve.csv
  📄 绩效指标 → output/20250530/1719/KAMA_metrics.csv
  📊 收益曲线图 → output/20250530/1719/KAMA_returns.png

==================================================
  回测绩效摘要
==================================================
  总收益率        :     0.4916
  年化收益率       :     1.0232
  基准收益率       :     0.0965
  超额收益        :     0.3952
  夏普比率        :     3.1428
  最大回撤        :    -0.0499
  胜率(日)       :     0.3706
  总交易次数       : 50
  止损次数        : 0
  止盈次数        : 4
  平均持股天数      : 7.7
==================================================
```

#### 各项指标解读

| 指标 | 含义 | 什么算好 |
|------|------|---------|
| **总收益率** | 从开始到结束赚了多少 | 越高越好 |
| **年化收益率** | 换算成一年的收益率 | >0.15 算不错 |
| **夏普比率** | 每承担1份风险换多少收益 | >1 可以，>2 很好 |
| **最大回撤** | 最惨的时候亏了多少 | 越小越好，> -0.2 要注意 |
| **胜率(日)** | 赚钱的天数占比 | >0.5 说明策略稳定 |
| **超额收益** | 比大盘多赚多少 | >0 说明跑赢了大盘 |

---

### 2. 多策略对比

想知道"哪个策略在我选的股票上表现最好"？用对比模式。

#### 2.1 查看可对比的策略

```bash
python run_compare.py --list

# 输出：
#   可用的信号策略:
#     KAMA
#     MACD_CDTD
#     ARBR
#     BOLL_DKBL
#     BOLL_TDCS
```

#### 2.2 对比所有策略

```bash
# 在所有demo股票上，对比全部5个策略
python run_compare.py

# 它会依次运行5次回测，然后生成对比报告
```

#### 2.3 对比指定的几个策略

```bash
# 只对比 KAMA 和 BOLL_DKBL
python run_compare.py --strategies KAMA,BOLL_DKBL
```

#### 2.4 自定义对比参数

```bash
python run_compare.py \
    --strategies KAMA,BOLL_DKBL,BOLL_TDCS \  # 对比这3个
    --stocks 000012,000014 \                  # 在这2只股票上
    --start 2023-01-01                        # 从2023年开始
```

#### 对比报告里有什么？

**CSV表格**（`output/comparison_*.csv`）：

| 策略名称 | 总收益率 | 年化收益率 | 夏普比率 | 最大回撤 | 交易次数 |
|---------|---------|-----------|---------|---------|---------|
| KAMA | 0.4916 | 1.0232 | 3.1428 | -0.0499 | 50 |
| BOLL_DKBL | 0.0712 | 0.2354 | 2.1136 | -0.0284 | 4 |

**收益曲线叠加图**（`output/comparison_*.png`）：
- 不同策略的收益率曲线用不同颜色画在一起
- 一眼看出哪个策略赚得多、哪个波动大

---

### 3. 参数优化

每个策略都有参数（比如KAMA的n、fast、slow）。**参数设置不同，结果天差地别**。优化模式帮你自动找到最佳参数组合。

#### 3.1 查看预置参数网格

```bash
python run_optimize.py --list-grids

# 输出（每个策略的可优化参数范围）：
#   KAMA:
#     n: [5, 10, 15, 20, 30]
#     fast: [2, 3]
#     slow: [20, 25, 30, 35, 40]
#   BOLL_DKBL:
#     period: [15, 20, 25, 30]
#     std_multiplier: [1.8, 2.0, 2.2]
#     volume_ratio: [1.3, 1.5, 1.8]
```

#### 3.2 运行参数优化

```bash
# 优化KAMA参数，以夏普比率为目标
python run_optimize.py --strategy KAMA

# 优化BOLL_DKBL参数，以卡玛比率为目标
python run_optimize.py --strategy BOLL_DKBL --objective calmar_ratio
```

**优化目标可选**（`--objective`）：

| 目标名称 | 含义 |
|---------|------|
| `total_return` | 总收益率 |
| `annualized_return` | 年化收益率 |
| `sharpe_ratio` | 夏普比率（默认） |
| `sortino_ratio` | Sortino比率 |
| `calmar_ratio` | 卡玛比率 |
| `win_rate` | 胜率 |
| `profit_factor` | 盈亏比 |

#### 3.3 自定义参数范围

```bash
# 只测试部分参数组合
python run_optimize.py \
    --strategy KAMA \
    --param-ranges '{"n": [5, 10, 15], "fast": [2], "slow": [25, 30, 35]}'
```

#### 3.4 只看最好的几个结果

```bash
python run_optimize.py --strategy KAMA --top-k 10
```

#### 优化完成后你会看到什么？

```
[参数优化] 目标: sharpe_ratio, 网格: 50 组参数
  参数范围: {'n': [5,10,15,20,30], 'fast': [2,3], 'slow': [20,25,30,35,40]}
--------------------------------------------------
  [1/50] {'n': 5, 'fast': 2, 'slow': 20}… ✓ sharpe_ratio=1.2345
  [2/50] {'n': 5, 'fast': 2, 'slow': 25}… ✓ sharpe_ratio=1.4567
  ...
  [50/50] {'n': 30, 'fast': 3, 'slow': 40}… ✓ sharpe_ratio=2.3456

============================================================
  🏆 最佳 5 组参数 (目标: sharpe_ratio)
============================================================
  #1: {'n': 15, 'fast': 2, 'slow': 30} → sharpe_ratio = 3.1428
  #2: {'n': 10, 'fast': 2, 'slow': 35} → sharpe_ratio = 2.9876
  ...

  📄 优化结果 → output/optimization_sharpe_ratio_xxx.csv
  📊 热力图 → output/optimization_heatmap_sharpe_ratio_xxx.png
```

**热力图**用颜色深浅直观展示参数组合的优劣——红色=好，绿色=差。

---

### 4. 添加新策略

想加入自己的交易策略？非常简单，只需要4步：

#### 第一步：在 `signals/` 下创建策略文件

```python
# signals/my_strategy.py
import pandas as pd
from core.signal_engine import BaseSignal


class MyStrategy(BaseSignal):
    """我的神奇策略：5日均线上穿20日均线买入，下穿卖出"""

    # 策略名称（用于列名前缀和信号文件名）
    name = 'MY_STRATEGY'

    # 参数（可以自己设默认值）
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
        }

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        这是唯一需要实现的方法。
        
        参数 data: 包含 date, open, high, low, close, volume 的DataFrame
        返回: 添加了 {name}_signal 列的 DataFrame
        
        信号约定:
          1  = 买入
          -1 = 卖出
          0  = 无操作
        """
        df = data.copy()

        # 算均线
        ma_fast = df['close'].rolling(self.params['fast_period']).mean()
        ma_slow = df['close'].rolling(self.params['slow_period']).mean()

        # 生成信号
        df['MY_STRATEGY_signal'] = 0

        # 上穿买入
        buy_cond = (ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))
        df.loc[buy_cond, 'MY_STRATEGY_signal'] = 1

        # 下穿卖出
        sell_cond = (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))
        df.loc[sell_cond, 'MY_STRATEGY_signal'] = -1

        return df
```

#### 第二步：在 `run_backtest.py` 中注册

```python
# 在文件开头的导入部分加上这行
from signals.my_strategy import MyStrategy

# 在 SIGNAL_FACTORY 字典里加上这行
SIGNAL_FACTORY = {
    'KAMA': KAMASignal,
    'MACD_CDTD': MACDCDTDSignal,
    'ARBR': ARBRSignal,
    'BOLL_DKBL': BOLLDKBLSignal,
    'BOLL_TDCS': BOLLTDCSignal,
    'MY_STRATEGY': MyStrategy,  # ← 加上这个
}
```

#### 第三步：运行回测

```bash
python run_backtest.py \
    --stocks 000012,000014 \
    --start 2022-01-01 \
    --signal MY_STRATEGY \
    --fast-period 5 \      # 你的策略参数
    --slow-period 20
```

> **注意**：框架会自动把参数名中的 `-` 转换为 `_`，所以 `--fast-period` 对应 `fast_period`。

#### 第四步：加入对比

```bash
# 你的策略和已有的策略一起对比
python run_compare.py --strategies KAMA,MY_STRATEGY
```

**总共只需要写一个类（约30行）+ 一行注册 + 一行命令，就完成了！**

---

## 📋 所有命令速查表

### 回测命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `--list-plans` | 查看预置方案 | `python run_backtest.py --list-plans` |
| `--plan <名称>` | 使用预置方案 | `python run_backtest.py --plan kama_demo` |
| `--stocks <代码>` | 指定股票 | `--stocks 000012,000014` |
| `--start <日期>` | 开始日期 | `--start 2022-01-01` |
| `--end <日期>` | 结束日期 | `--end 2024-12-31`（不填=最新） |
| `--signal <策略>` | 策略名称 | `--signal KAMA` |
| `--tag <标记>` | 文件命名标记 | `--tag my_test` |
| `--money <金额>` | 每只股票初始资金 | `--money 50000`（默认10000） |
| `--slippage <值>` | 滑点 | `--slippage 0.001`（默认0.003） |
| `--commission <值>` | 佣金比例 | `--commission 0.0003`（默认万分之五） |
| `--tax <值>` | 印花税比例 | `--tax 0.0005`（默认千分之一） |
| `--stop-loss <值>` | 止损比例 | `--stop-loss 0.03`（默认5%） |
| `--stop-profit <值>` | 止盈比例 | `--stop-profit 0.15`（默认20%） |
| `--drawdown <值>` | 回落止盈比例 | `--drawdown 0.02`（默认3%） |

### 策略参数（策略特有）

| 策略 | 参数 | 说明 | 默认值 |
|------|------|------|--------|
| KAMA | `--n` | 效率比率周期 | 10 |
| KAMA | `--fast` | 快线参数 | 2 |
| KAMA | `--slow` | 慢线参数 | 30 |
| MACD_CDTD | `--fast-period` | 快线周期 | 12 |
| MACD_CDTD | `--slow-period` | 慢线周期 | 26 |
| MACD_CDTD | `--signal-period` | 信号线周期 | 9 |
| ARBR | `--period` | 计算周期 | 26 |
| ARBR | `--ar-threshold` | AR阈值 | 150 |
| ARBR | `--br-threshold` | BR阈值 | 50 |
| BOLL_DKBL | `--period` | 布林周期 | 20 |
| BOLL_DKBL | `--std-multiplier` | 标准差倍数 | 2.0 |
| BOLL_DKBL | `--volume-ratio` | 成交量放大倍率 | 1.5 |

### 对比命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `--list` | 列出可对比策略 | `python run_compare.py --list` |
| `--strategies` | 选择策略对比 | `--strategies KAMA,BOLL_DKBL` |
| `--stocks` | 指定股票 | `--stocks 000012,000014` |
| `--start` | 开始日期 | `--start 2023-01-01` |
| `--end` | 结束日期 | `--end 2024-12-31` |

### 优化命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `--list-grids` | 查看预置参数网格 | `python run_optimize.py --list-grids` |
| `--strategy` | 选择优化策略 | `--strategy KAMA` |
| `--objective` | 优化目标 | `--objective sharpe_ratio` |
| `--param-ranges` | 自定义参数范围 | `--param-ranges '{"n":[5,10,15]}'` |
| `--top-k` | 输出最佳组合数 | `--top-k 10`（默认5） |
| `--stocks` | 指定股票 | `--stocks 000012` |
| `--start` | 开始日期 | `--start 2022-01-01` |

---

## 🔍 各模块详解

### 核心模块（`core/`）

| 文件 | 类名 | 一句话说明 |
|------|------|-----------|
| `data_loader.py` | `DataLoader` | 从CSV读股票数据，清洗、校验、裁剪日期 |
| `signal_engine.py` | `SignalEngine` | 用注册的策略计算买卖信号，合成仓位 |
| `signal_engine.py` | `BaseSignal` | **所有策略的爸爸**，新策略继承它 |
| `risk_manager.py` | `RiskManager` | 止盈止损、涨跌停限制 |
| `equity_curve.py` | `EquityCurveCalculator` | 根据买卖信号算每天赚了多少钱 |
| `metrics.py` | `MetricsCalculator` | 算夏普比率、最大回撤等绩效指标 |
| `reporter.py` | `Reporter` | 把结果保存为CSV和图表 |
| `engine.py` | `BacktestEngine` | **总指挥**，把上面所有模块串起来 |
| `comparator.py` | `StrategyComparator` | 多策略对比 |
| `optimizer.py` | `ParameterOptimizer` | 参数网格优化 |

#### 回测引擎（`BacktestEngine`）的5步流水线

```
Step 1: DataLoader.load_stock_batch()   →  加载股票数据
Step 2: SignalEngine.generate()         →  计算买卖信号
Step 3: RiskManager.apply_*()           →  施加风控
Step 4: EquityCurveCalculator.compute() →  算资金曲线
Step 5: MetricsCalculator + Reporter    →  算指标 + 输出报告
```

### 策略模块（`signals/`）

| 文件 | 类名 | 策略思路 |
|------|------|---------|
| `kama.py` | `KAMASignal` | 自适应均线，价格上穿/下穿KAMA线 |
| `macd_cdtd.py` | `MACDCDTDSignal` | MACD柱状图面积递减=底背离买入，高度递减=顶背离卖出 |
| `arbr.py` | `ARBRSignal` | AR上穿150（恐慌）+ BR下穿50（悲观）= 诱空买入 |
| `boll_dkbl.py` | `BOLLDKBLSignal` | 布林带收口后价格突破方向 = 变盘信号 |
| `boll_tdcs.py` | `BOLLTDCSignal` | 价格在布林带位置 + RSI + MACD = 综合判断 |

---

## ❓ 常见问题

### Q1: 我改了代码，但运行还是原来的效果？

- 检查是否保存了文件
- 检查终端是否在项目根目录（`002_self_backtest_reborn/`）
- 如果是新增的策略：检查 `run_backtest.py` 里的 `SIGNAL_FACTORY` 是否注册了

### Q2: 报错 "股票数据文件不存在"？

- 确认股票代码是否存在（输入 6 位数字，如 `000012`）
- 确认数据目录 `/public/home/hpc/zhulei/superman/quant/data/input/` 下有对应的 CSV 文件
- 确认股票代码没有前导的 `sh.` 或 `sz.`

### Q3: 报错 "股票为ST股" 或 "为次新股"？

- ST 股（退市风险股）会自动跳过
- 次新股（上市不足240个交易日）会自动跳过
- 这是框架的风控逻辑，不是 bug

### Q4: 回测结果很差怎么办？

试试：
1. **参数优化**：`python run_optimize.py --strategy KAMA` 找最佳参数
2. **换策略**：`python run_compare.py --strategies KAMA,BOLL_DKBL,MACD_CDTD`
3. **调整风控**：收紧止损 `--stop-loss 0.03`，或者放宽止盈 `--stop-profit 0.30`
4. **换时间段**：不同行情适合不同策略

### Q5: 怎么添加自己的股票池？

编辑 `config/backtest_config.py`，在 `STOCK_POOLS` 字典里添加：

```python
STOCK_POOLS = {
    'my_picks': [
        '000001', '000002', '000651', '000333', '000858',
    ],
    # ... 已有的
}
```

然后使用：`python run_backtest.py --plan my_plan`

> 注意：还需要在 `BACKTEST_PLANS` 中定义一个使用 `my_picks` 的方案。

### Q6: 我想只跑1只股票快速测试？

```bash
python run_backtest.py --stocks 000012 --start 2024-01-01 --end 2024-06-30
```

### Q7: 输出文件在哪里？

输出目录按**日期/时间**自动分层组织，不同时间运行的结果互不干扰：

```
output/
├── 20250530/               ← 运行回测的日期（YYYYMMDD）
│   └── 1719/               ← 运行回测的时间（HHMM，24小时制）
│       ├── KAMA_trade_records.csv   ← 交易明细
│       ├── KAMA_account_curve.csv   ← 每天的总资产、现金、股票市值
│       ├── KAMA_metrics.csv         ← 各项绩效指标汇总
│       └── KAMA_returns.png         ← 收益率曲线图
├── 20250531/               ← 明天再跑就自动新建目录
│   └── 0902/
│       ├── KAMA_trade_records.csv
│       └── ...
└── ...
```

**文件名说明**：
- `KAMA_*.csv` — 前缀 = 策略名称（`--tag` 参数可自定义）
- `trade_records` — 每笔交易的买入卖出明细
- `account_curve` — 账户每日资金曲线（含基准对比）
- `metrics` — 各项绩效指标汇总
- `returns.png` — 收益率曲线对比图

---

## 🚀 下一步可以做什么？

- [x] 添加更多策略（如 RSI、KDJ、VOL 等）
- [x] 更多股票池（全A股扫描）
- [x] 异步并行回测（加快多股票回测速度）
- [x] 机器学习信号（结合 XGBoost/LSTM 生成信号）
- [x] 实时信号 + 自动交易

---

> **Happy Quanting! 🚀** — 有问题随时问
