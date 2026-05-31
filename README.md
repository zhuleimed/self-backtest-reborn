# 📈 模块化量化回测框架

> **002_self_backtest_reborn** — 基于 GF 指标公式库（97 个技术指标）的 A 股回测系统

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![GitHub](https://img.shields.io/badge/GitHub-self--backtest--reborn-green)](https://github.com/zhuleimed/self-backtest-reborn)

---

## 📑 目录

- [一分钟快速上手](#-一分钟快速上手)
- [项目结构](#-项目结构)
- [回测命令详解](#-回测命令详解run_backtestpy)
- [多指标对比](#-多指标对比run_comparepy)
- [参数优化](#-参数优化run_optimizepy)
- [可用指标一览](#-可用指标一览)
- [输出结果解读](#-输出结果解读)
- [自定义参数说明](#-自定义参数说明)
- [常见问题](#-常见问题)

---

## ⚡ 一分钟快速上手

```bash
# 1. 进到项目目录
cd /public/home/hpc/zhulei/superman/quant/code/002_self_backtest_reborn

# 2. 查看所有可用的技术指标（共 97 个）
python run_backtest.py --list-indicators

# 3. 运行回测（KDJ 指标，单只股票）
python run_backtest.py --stocks 000012 --indicator KDJ

# 4. 多指标组合（宽松买入+严格卖出）
python run_backtest.py --stocks 000012 --indicators KDJ,RSI --combo-mode strict_buy

# 5. 全量指标对比（自动排序，看 Top 5）
python run_compare.py --strategies ALL --stocks 000012 --top-n 5

# 6. 看结果
ls output/20260530/1850/
```

---

## 🏗 项目结构

```
002_self_backtest_reborn/
│
├── run_backtest.py           ← 🚀 回测入口（主要使用）
├── run_compare.py            ← 🚀 多指标对比入口
├── run_optimize.py           ← 🚀 参数优化入口
├── config/
│   └── backtest_config.py    ← 默认配置（含97个指标列表注释）
│
├── core/                     ← ⚙️ 回测引擎模块
│   ├── engine.py             ← 回测总编排器（5步流水线）
│   ├── data_loader.py        ← 数据加载与清洗
│   ├── signal_engine.py      ← 信号合成引擎
│   ├── risk_manager.py       ← 风控（止盈止损、涨跌停）
│   ├── equity_curve.py       ← 资金曲线计算
│   ├── metrics.py            ← 绩效指标计算
│   ├── reporter.py           ← 结果输出与图表
│   ├── comparator.py         ← 多指标对比
│   └── optimizer.py          ← 参数网格优化
│
├── signals/                  ← 📦 GF 综合指标策略
│   ├── gf.py                 ← 统一策略入口（97个指标）
│   └── gf_factors.py         ← 指标计算函数库（143个函数）
│
├── output/                   ← 📊 回测结果（自动生成）
│   ├── 20250530/             ← 日期目录
│   │   ├── 1719/             ← 时间目录
│   │   │   ├── KDJ_trade_records.csv
│   │   │   ├── KDJ_account_curve.csv
│   │   │   ├── KDJ_metrics.csv
│   │   │   └── KDJ_returns.png
│   │   └── 1820/             ← 下一次运行
│   └── ...
│
├── .claude/                  ← Claude Code 配置（勿动）
├── CLAUDE.md                 ← 项目说明
└── README.md                 ← 本指南
```

---

## 📖 回测命令详解（`run_backtest.py`）

### 运行示例

```bash
# 最简模式（必填：股票 + 指标）
python run_backtest.py --stocks 000012 --indicator KDJ

# 多只股票 + 指定时间 + 自定义指标参数
python run_backtest.py \
    --stocks 000012,000014,000016 \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --indicator MACD \
    --n1 10 \
    --n2 24 \
    --n3 7

# 自定义风控参数
python run_backtest.py \
    --stocks 000012 \
    --indicator RSI \
    --stop-loss 0.03 \
    --stop-profit 0.15 \
    --money 50000

# 自定义标签（输出文件前缀）
python run_backtest.py --stocks 000012 --indicator KDJ --tag my_test

# 多指标组合（严格模式：同步买入，同步卖出）
python run_backtest.py \
    --stocks 000012 \
    --indicators MACD,RSI \
    --combo-mode all_agree

# 多指标组合（宽松买入+严格卖出：同步买入，任一卖出即卖）
python run_backtest.py \
    --stocks 000012 \
    --indicators KDJ,RSI,MACD \
    --combo-mode strict_buy
```

### 参数列表

#### 基本参数

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `--stocks` | 字符串 | ✅ | 股票代码，多只逗号分隔，如 `000012,000014` | — |
| `--start` | 字符串 | ❌ | 开始日期 `YYYY-MM-DD` | `2022-01-01` |
| `--end` | 字符串 | ❌ | 结束日期 `YYYY-MM-DD`，不填=到最新 | 最新 |
| `--indicator` | 字符串 | ❌ | 单个技术指标名称（大写）。查看全部: `--list-indicators` | `KDJ` |
| `--indicators` | 字符串 | ❌ | 多指标组合，逗号分隔。配合 `--combo-mode` 使用 | — |
| `--combo-mode` | 枚举 | ❌ | 多指标组合模式: `all_agree`(严格) / `strict_buy`(宽松买+严格卖) | `all_agree` |
| `--tag` | 字符串 | ❌ | 输出文件名前缀 | 指标名_开始日期 |
| `--list-indicators` | 标志 | ❌ | 列出全部 97 个指标 | — |

#### 指标参数覆盖（不同指标含义不同，见 `signals/gf.py` 中的 `_DEFAULT_PARAMS`）

| 参数 | 类型 | 说明 | 适用指标示例 |
|------|------|------|-------------|
| `--n` | 整数 | 主周期参数 | KDJ(N)、RSI(N)、CCI(N)、WR(N) |
| `--n1` | 整数 | 参数1 | MACD(N1=快线周期)、OBV(N1) |
| `--n2` | 整数 | 参数2 | MACD(N2=慢线周期)、OBV(N2) |
| `--n3` | 整数 | 参数3 | MACD(N3=信号线周期) |
| `--m` | 整数 | 辅助周期 | SKDJ(M)、TYP(M) |

#### 资金与交易成本

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--money` | 浮点数 | 每只股票初始资金（元） | `10000` |
| `--slippage` | 浮点数 | 滑点（买入上浮、卖出入下比例） | `0.003` (0.3%) |
| `--commission` | 浮点数 | 佣金比例（最低5元） | `0.0005` (万分之五) |
| `--tax` | 浮点数 | 印花税比例（卖出时收取） | `0.001` (千分之一) |
| `--position` | 浮点数 | 每笔交易仓位比例 | `0.95` (95%) |

#### 风控参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--stop-loss` | 浮点数 | 止损比例：开盘价 < 买入价×(1−比例) 时卖出 | `0.05` (5%) |
| `--stop-profit` | 浮点数 | 止盈触发比例：最高价 ≥ 买入价×(1+比例) 时激活 | `0.20` (20%) |
| `--drawdown` | 浮点数 | 回落止盈比例：止盈激活后，开盘价 < 最高价×(1−比例) 时卖出 | `0.03` (3%) |

### 参数常见错误

```bash
# ❌ 错误：参数名不对
python run_backtest.py --stocks 300730 --start_date 2026-01-01

# ✅ 正确
python run_backtest.py --stocks 300730 --start 2026-01-01

# ❌ 错误：用等号赋值
python run_backtest.py --stop-loss=0.03

# ✅ 正确（用空格分隔）
python run_backtest.py --stop-loss 0.03
```

### 运行过程输出

```
[回测引擎] 开始回测: KDJ_2024-01-01
  股票池: 3 只
  时间:   2024-01-01 → 2024-12-31
  策略:   GF
  输出:   output/20250530/1719/
--------------------------------------------------
[1/5] 加载数据…
  ✓ 加载 3 只股票, 1 个基准指数
[2/5] 生成交易信号…
  ✓ 信号策略: GF
[3/5] 施加风控规则…
[4/5] 计算资金曲线…
[5/5] 计算绩效 & 生成报告…
  📄 交易记录 → output/20250530/1719/KDJ_trade_records.csv
  📄 资金曲线 → output/20250530/1719/KDJ_account_curve.csv
  📄 绩效指标 → output/20250530/1719/KDJ_metrics.csv
  📊 收益曲线图 → output/20250530/1719/KDJ_returns.png
```

---

## 📖 多指标对比（`run_compare.py`）

在相同的股票和时间范围下，同时运行多个指标并对比结果。

```bash
# 列出所有可用指标
python run_compare.py --list

# 对比 4 个常用指标（默认）
python run_compare.py

# 对比指定的几个指标
python run_compare.py --strategies KDJ,MACD,RSI

# 自定义股票和参数
python run_compare.py \
    --strategies KDJ,RSI,CCI \
    --stocks 000012,000014 \
    --start 2023-01-01 \
    --money 50000 \
    --stop-loss 0.03

# 全量对比所有97个指标，仅显示 Top 5 图表
python run_compare.py --strategies ALL --stocks 000012 --top-n 5
```

### 对比参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--strategies` | 字符串 | 指标名称逗号分隔。`ALL`=全量对比97个指标 | `KDJ,RSI,MACD,CCI` |
| `--top-n` | 整数 | 全量对比时图表显示 Top N 个最佳指标（默认8） | `8` |
| `--stocks` | 字符串 | 股票代码 | 配置文件默认 |
| `--start` | 字符串 | 开始日期 | 配置文件默认 |
| `--end` | 字符串 | 结束日期 | 最新 |
| `--list` | 标志 | 列出所有指标 | — |
| `--money` | 浮点数 | 每只股票初始资金 | 10000 |
| `--stop-loss` | 浮点数 | 止损比例 | 0.05 |

---

## 📖 参数优化（`run_optimize.py`）

自动搜索指标的最佳参数组合。

```bash
# 查看所有预置参数网格
python run_optimize.py --list-grids

# 优化 KDJ 参数（目标：夏普比率）
python run_optimize.py --indicator KDJ

# 优化 MACD 参数（目标：卡玛比率）
python run_optimize.py --indicator MACD --objective calmar_ratio

# 自定义搜索范围和股票
python run_optimize.py \
    --indicator KDJ \
    --param-ranges '{"N": [30, 40, 50]}' \
    --stocks 000012 \
    --top-k 10
```

### 优化目标

| 参数值 | 中文含义 |
|--------|---------|
| `total_return` | 总收益率 |
| `annualized_return` | 年化收益率 |
| `sharpe_ratio` | 夏普比率（默认） |
| `sortino_ratio` | Sortino 比率 |
| `calmar_ratio` | 卡玛比率 |
| `win_rate` | 胜率 |
| `profit_factor` | 盈亏比 |

### 优化参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--indicator` | 字符串 | 要优化的指标名称 | `KDJ` |
| `--objective` | 字符串 | 优化目标 | `sharpe_ratio` |
| `--param-ranges` | JSON | 自定义参数范围 | 预置网格 |
| `--top-k` | 整数 | 输出最佳组合数 | `5` |
| `--stocks` | 字符串 | 股票代码 | 配置文件 |
| `--start` | 字符串 | 开始日期 | 配置文件 |
| `--list-grids` | 标志 | 列出预置网格 | — |

### 优化结果示例

```
[参数优化] 目标: sharpe_ratio, 网格: 25 组参数
--------------------------------------------------
  [1/25] {'N': 20}… ✓ sharpe_ratio=1.2345
  [2/25] {'N': 30}… ✓ sharpe_ratio=1.5678
  ...

  🏆 最佳 5 组参数 (目标: sharpe_ratio)
  #1: {'N': 30} → sharpe_ratio = 3.1428
  #2: {'N': 40} → sharpe_ratio = 2.9876
```

---

## 📋 可用指标一览

共 **97 个技术指标**，分为以下 5 大类：

### 价格动量指标（62 个）

```
DPO  ER  TII  PO  MA_DISPLACED  T3  POS  PAC  ADTM
ZLMACD  TMA  TYP  KDJD  VMA  BIAS  WMA_M  DDI  HMA
SROC  EXPMA  DC  VIDYA  QSTICK  FB  DEMA  APZ  ASI
ARRON  KC  MTM  CR  BOP  HULLMA  COPP  ENV  RSIH
HLMA  TSI  BIAS36  UOS  DZRSI  DZCCI  CMF  PPO  RWI
ATR  WAD  KST  VI  DMA_I  MICD  PMO  RCCD  KAMA  AWS
ARBR  ADXR  SMI  SI  DO  DBCD  CV
```

### 价格反转指标（10 个）

```
KDJ  RMI  SKDJ  CCI  RSI  ROC  WR  STC  RVI  RSIS
```

### 成交量指标（6 个）

```
MAAMT  SROCVOL  PVO  BIASVOL  MACDVOL  ROCVOL
```

### 价量指标（17 个）

```
VWAP  FI  NVI  PVT  RSIV  AMV  VRAMT  WVAD  OBV
PVI  TMF  MFI  ADOSC  VAO  VR  KO  EMV
```

### 混合指标（1 个）

```
MACD
```

> **说明**：在命令行中使用时，直接写指标名（**大写**），如 `--indicator MACD`、

---

## 📊 输出结果解读

### 绩效指标

| 指标 | 含义 | 说明 |
|------|------|------|
| 总收益率 | 回测期间总收益 / 初始资金 | >0 表示盈利 |
| 年化收益率 | 按 252 个交易日折算的年收益 | >0.15 较好 |
| 基准收益率 | 同期沪深300涨跌幅 | 对比策略是否跑赢大盘 |
| 超额收益 | 策略收益 - 基准收益 | >0 说明跑赢大盘 |
| 夏普比率 | (收益 - 无风险利率) / 波动率 | >1 可用，>2 优秀 |
| Sortino比率 | 同上，但只计算下行波动 | 越大越好 |
| 最大回撤 | 最高点到最低点的最大跌幅 | 越小越安全 |
| 胜率(日) | 正收益天数占比 | >0.5 说明策略稳定 |
| 总交易次数 | 买入+卖出总次数 | 越多说明交易越频繁 |
| 止损次数 | 触发了止损的次数 | 仅供参考 |
| 止盈次数 | 触发了止盈的次数 | 越高越好 |

### 输出文件

路径格式：`output/YYYYMMDD/HHMM/`

| 文件 | 内容 |
|------|------|
| `*_trade_records.csv` | 每笔交易的买卖明细 |
| `*_account_curve.csv` | 每日资金曲线 |
| `*_metrics.csv` | 绩效指标汇总 |
| `*_returns.png` | 收益曲线图（策略 vs 基准） |

---

## ❓ 常见问题

### Q1: 必须指定哪些参数？

最少只需要 `--stocks` 和 `--indicator`：

```bash
python run_backtest.py --stocks 000012 --indicator KDJ
```

### Q2: 怎么看有哪些指标可用？

```bash
python run_backtest.py --list-indicators
```

### Q3: 怎么看每个指标的默认参数？

查看 `config/backtest_config.py` 中注释部分的指标列表，
以及 `signals/gf.py` 中的 `_DEFAULT_PARAMS` 字典。

### Q4: 运行报错 "股票数据文件不存在"？

- 确认股票代码是 6 位数字（如 `000012`）
- 确认数据目录 `/public/home/hpc/zhulei/superman/quant/data/input/` 下有对应 CSV

### Q5: 运行报错 "股票为ST股" 或 "为次新股"？

- ST 股（退市风险股）框架自动跳过
- 次新股（上市不足 240 个交易日）自动跳过
- 不是 bug，是风控逻辑

### Q6: 输出文件在哪里？

```bash
# 查看按日期时间组织的输出
ls output/20260530/1719/
```

### Q7: 参数名后面的 `--` 和变量名有什么区别？

命令行参数用 `--stop-loss`（横线），代码内部用 `stop_loss_pct`（下划线）。
框架会自动转换，不用操心。

### Q8: 不同时间运行的结果会互相覆盖吗？

**不会**。每次运行都会生成 `output/YYYYMMDD/HHMM/` 时间目录，完全隔离。

### Q9: 回测结果和真实交易会有偏差吗？

框架做了以下修正以消除未来函数（look-ahead bias）：

1. **信号后移一天**：所有买卖信号在生成后整体后移一天。`pos[i]` 反映 `i-1` 日的信号，在 `i` 日开盘执行。这样信号使用的 `close` 数据在交易之前就已经是已知信息
2. **次日开盘成交**：所有交易以信号产生后的 **次日开盘价** 成交，不是当日收盘价
3. **虚拟卖出**：回测到期仍持有的股票，以最后一日收盘价虚拟卖出，形成完整闭环

### Q10: 多指标组合和单指标回测有什么区别？

- **单指标**：使用 `--indicator` 参数，运行一个技术指标的信号
- **多指标组合**：使用 `--indicators` 参数（复数），指定多个指标，通过 `--combo-mode` 控制信号合成规则
  - `all_agree`：所有指标同时买入才买，同时卖出才卖
  - `strict_buy`：所有指标同时买入才买，任一卖出就卖

---

> **Happy Quanting! 🚀**
