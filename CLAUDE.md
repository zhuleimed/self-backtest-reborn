# 002_self_backtest_reborn

模块化量化回测框架，基于 GF 指标公式库（97 个技术指标），面向 A 股日线回测。

## 项目架构

```
run_backtest.py      ← 主要入口：单指标回测
run_compare.py       ← 多指标横向对比
run_optimize.py      ← 参数网格优化
|
+-- config/
|   +-- backtest_config.py   默认配置字典 (DEFAULT_CONFIG)
|
+-- core/                    回测引擎流水线
|   +-- engine.py            BacktestEngine 总编排器（5步流水线）
|   +-- data_loader.py       DataLoader：本地 CSV → DataFrame（含ST/次新股过滤）
|   +-- signal_engine.py     SignalEngine + BaseSignal 基类
|   +-- risk_manager.py      RiskManager：涨跌停限制、固定/移动止盈止损
|   +-- equity_curve.py      EquityCurveCalculator：单股票+账户聚合资金曲线
|   +-- metrics.py           绩效指标计算（夏普、Sortino、Calmar等）
|   +-- reporter.py          报告生成（CSV + Matplotlib 对比图）
|   +-- comparator.py        多策略对比器（StrategyComparator）
|   +-- optimizer.py         参数网格优化器（ParameterOptimizer）
|   +-- log_utils.py         彩色日志工具
|
+-- signals/
|   +-- gf.py                GFSignal：唯一策略类，含97个指标信号方法
|   +-- gf_factors.py        2377行，143+个技术指标计算函数（numpy实现）
|
+-- output/                  回测结果按日期/时间分层
|   +-- 20260531/
|       +-- 0915/
|           +-- KDJ_trade_records.csv
|           +-- KDJ_account_curve.csv
|           +-- KDJ_metrics.csv
|           +-- KDJ_returns.png
|
+-- .claude/                 Claude Code 技能与命令
|   +-- commands/run-backtest.md
|   +-- skills/ (data-loader, signal-generator, risk-manager, equity-calc, report-builder)
```

## 核心数据流

```
CSV (../data/input/000012.csv)
  │ 必需列: date, open, high, low, close, volume, amount, isST
  │
  ▼ [data_loader.py]
DataLoader.load_stock_batch()
  │ 过滤: ST股跳过, 次新股(不足240日)跳过
  │ 清洗: 日期转换, 数值类型, 日期裁剪
  │ 派生: pct_chg, cumulative_returns
  ▼
DataFrame (index=date, 含 open/high/low/close/volume/amount/pct_chg/cumulative_returns)

  ▼ [signal_engine.py]
SignalEngine.generate()
  │ 调用注册策略的 compute() → 添加 {name}_signal 列 (1=买入, -1=卖出, 0=持有)
  │ 合成 → pos 列 (0/1, 前向填充)
  ▼
DataFrame (新增 pos, {name}_signal)

  ▼ [risk_manager.py]
RiskManager.apply_limit_up_down()        # 涨跌停限制
RiskManager.apply_stop_strategy()        # 固定止盈止损
  │ 新增: stop_signal, buy_price, highest_price, position_status
  ▼
DataFrame (修正 pos, 新增 stop_signal)

  ▼ [equity_curve.py]
EquityCurveCalculator.compute_single()   # 每只股票
  │ 逐行计算: hold_num, cash, stock_value, equity
  │ 整百股交易, 含滑点/佣金/印花税
  │ 期末未平仓 → 虚拟卖出
  ▼
{equity_curve, trade_records}

  ▼ [metrics.py + reporter.py]
MetricsCalculator.compute()              # 账户聚合 + 绩效指标
Reporter.save_*()                        # CSV + PNG
```

## 回测命令

### 单指标回测

```bash
# 最小必填参数
python run_backtest.py --stocks 000012 --indicator KDJ

# 查看所有可用指标（97个）
python run_backtest.py --list-indicators

# 常用完整模式
python run_backtest.py \
  --stocks 000012,000014,000016 \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --indicator MACD \
  --money 50000 \
  --stop-loss 0.03 \
  --tag my_test
```

支持参数（见 `run_backtest.py` 的 `parse_args()`）：
- 策略参数：`--indicator`, `--indicators`, `--combo-mode`, `--n`, `--n1`, `--n2`, `--n3`, `--m`
- 资金：`--money`, `--slippage`, `--commission`, `--tax`, `--position`
- 风控：`--stop-loss`, `--stop-profit`, `--drawdown`, `--trailing-stop`, `--trailing-profit`
- 性能：`--workers`（`run_backtest.py` 回测内多股票并行线程数，默认4；`run_compare.py` 策略间并行线程数，默认1）

### 多指标组合信号

将多个技术指标的买卖信号按规则合成一个信号，实现更稳健的交易决策。

```bash
# 严格模式（all_agree）：所有指标同时买入才买，同时卖出才卖
python run_backtest.py --stocks 000012 \
  --indicators MACD,RSI \
  --combo-mode all_agree

# 宽松买入+严格卖出（strict_buy）：所有买入才买，任一卖出就卖
python run_backtest.py --stocks 000012 \
  --indicators KDJ,RSI,MACD \
  --combo-mode strict_buy
```

两种组合模式：

| 模式 | 买入 | 卖出 | 适用场景 |
|------|------|------|----------|
| `all_agree` | 所有指标 = 1 | 所有指标 = -1 | 严格过滤，减少噪音交易 |
| `strict_buy` | 所有指标 = 1 | 任一指标 = -1 | 买入谨慎，卖出果断 |

> 注：`--indicators` 与 `--indicator` 互斥，前者用于多指标组合，后者用于单指标。
> `--n / --n1 / --n2 / --n3 / --m` 等参数会同时传递给所有子指标。

实现类：`signals/gf.py` 中的 `ComboGFSignal`，直接调用各指标的 `_signal_{NAME}()` 方法获取原始信号，再按规则合成。不经过 `GFSignal.compute()` 的列重命名步骤。

### 多指标对比

```bash
# 对比 4 个常用指标
python run_compare.py

# 指定指标对比
python run_compare.py --strategies KDJ,MACD,RSI,CCI

# 全量对比（所有 97 个指标，自动跳过未实现的）
python run_compare.py --strategies ALL --stocks 000012 --top-n 5

# 自定义参数
python run_compare.py --strategies KDJ,RSI --stocks 000012 --start 2023-01-01
```

生成：对比 CSV 表（按总收益率降序排列）+ 控制台 Top-N 排行榜 + 多策略叠加曲线图 + 绩效雷达图。
- `--strategies ALL` 遍历 `GFSignal.INDICATORS` 全部指标，**耗时较长**
- `--workers N` 启用 N 线程并行对比，全量对比时建议 `--workers 4~8`
- `--top-n` 控制图表显示前 N 个最佳策略（默认 8）
- 对比时自动跳过信号方法未实现或参数异常的指标

### 参数优化

```bash
# 查看预置网格
python run_optimize.py --list-grids

# 优化 KDJ 参数（默认目标：夏普比率）
python run_optimize.py --indicator KDJ

# 自定义参数范围和优化目标
python run_optimize.py \
  --indicator KDJ \
  --param-ranges '{"N": [20, 30, 40, 50]}' \
  --objective calmar_ratio \
  --top-k 10
```

## 信号体系

### 唯一策略类：GFSignal

`signals/gf.py` 中 `GFSignal` 是**唯一的策略实现**。全部 **97 个指标**均已实现完整的 `_signal_{INDICATOR_NAME}()` 方法，可通过 `--strategies ALL` 一键全量对比。

```python
# 关键设计
class GFSignal(BaseSignal):
    name = 'GF'

    # compute() 是入口 — 调用 self.params['indicator'] 对应的 _signal_XXX 方法
    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        method = getattr(self, f'_signal_{self._indicator}')
        df = method(data)
        # 将 {INDICATOR}_signal → GF_signal
        df['GF_signal'] = df[f'{self._indicator}_signal']
        return df
```

### 信号生成模式

五种核心模式，见于 `gf.py` 各 `_signal_XXX` 方法：

| 模式 | 规则 | 示例指标 |
|------|------|----------|
| **CROSS_ZERO** | 上穿0买入/下穿0卖出 | SROC, MTM, FI, PVO, PO |
| **CROSS_MA** | 价格上穿均线买入/下穿卖出 | HMA, KAMA, AWS, VWAP |
| **CROSS_THRESHOLD** | 穿越固定阈值 | KDJ(20/80), RSI(40/60), CCI(±100) |
| **CROSS_LINE** | 两线交叉 | MACD(DIF/DEA), TYP, OBV |
| **BAND** | 突破轨道 | PAC, ENV |

### 多指标组合：ComboGFSignal

`signals/gf.py` 中的 `ComboGFSignal` 支持将多个指标的信号按规则合成：

```python
class ComboGFSignal(BaseSignal):
    name = 'GF'  # 最终仍输出 GF_signal 列，不改变下游流水线
```

实现原理：直接调用各子指标的 `_signal_{NAME}()` 方法获取原始 `{NAME}_signal` 列，
然后按组合规则（`all_agree` / `strict_buy`）合成单一 `GF_signal` 列。
不经过 `GFSignal.compute()` 的列重命名步骤，避免子信号被覆盖。

### 添加新指标

1. 在 `GFSignal.INDICATORS` 列表添加指标名（大写）
2. 在 `GFSignal._DEFAULT_PARAMS` 添加默认参数字典
3. 实现 `_signal_{NAME}()` 方法，添加 `{NAME}_signal` 列（值：1/-1/0）

> **注意**：`INDICATORS` 列表的指标必须与 `_DEFAULT_PARAMS` 和 `_signal_{NAME}` 方法一一对应。新增指标时三条都要加。
> 缺少对应 `_signal_` 方法的指标会在运行时抛出 `NotImplementedError`，对比模式会跳过。

## 风控体系

### 固定止盈止损（默认，`run_backtest.py` 参数可调）

- **止损**：开盘价 < 买入价 × (1 - stop_loss_pct) → 卖出
- **止盈**：最高价 ≥ 买入价 × (1 + stop_profit_pct) 激活 → 开盘价 < 最高价 × (1 - drawdown_pct) → 卖出
- **涨跌停限制**：涨停开板无法买入，跌停开板无法卖出

### 移动止损（需显式启用 `--trailing-stop`）

- 涨幅超过 `trailing_profit_pct` 后激活
- 从最高价回落 `trailing_stop_pct` → 卖出

`stop_signal` 列编码：-1=止损, -2=止盈, -3=策略卖出

## 数据来源

- **股票日线**：`../data/input/` 目录下的 `{6位代码}.csv`，列含 `date, open, high, low, close, volume, amount, isST`
- **基准指数**：通过 `baostock` API 获取沪深300日线（`sh.000300`）
- 股票自动过滤：ST 股、次新股（不足240个交易日）

## 输出结构

每次运行生成 `output/YYYYMMDD/HHMM/` 目录（日期+时间，永远不会互相覆盖）：
- `*_trade_records.csv` — 每笔交易的买卖明细（含分单处理）
- `*_account_curve.csv` — 每日资金曲线（多股票聚合）
- `*_metrics.csv` — 绩效指标汇总
- `*_returns.png` — 策略 vs 基准收益曲线

## 关键技术细节

- **全局信号约定**：`1` = 买入, `-1` = 卖出, `0` = 无操作；`pos` 列：`1` = 持仓, `0` = 空仓
- **交易行为**：以次日 `open` 成交（非当日 close），含双边滑点（默认0.3%）
- **时序修正**：信号在 `_generate_signals()` 末尾整体后移一天（`shift(1)`），消除 look-ahead bias。即 `pos[i]` 反映 `i-1` 日的信号，在 `i` 日开盘执行
- **最小交易单位**：100股（整手），`theory_num // 100 * 100`
- **佣金最低5元**：`max(buy_cost * commission_rate, 5.0)`
- **持仓会计**：FIFO 卖出（买入订单队列先进先出），含分单利润分摊
- **并行回测**：`ThreadPoolExecutor` + `max_workers`（默认4），仅资金曲线步骤并行
- **中文字体**：`Noto Sans CJK JP`，位于 `/usr/share/fonts/opentype/noto/`

## 关键文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `signals/gf_factors.py` | ~2377 | 底层指标计算，numpy 实现（REF/SMA/EMA/HHV/LLV 等 143+ 函数） |
| `signals/gf.py` | ~1378 | 策略编排，全部 97 个 `_signal_XXX()` 方法已实现 |
| `core/engine.py` | ~320 | 5 步流水线编排，配置 dataclass |
| `core/equity_curve.py` | ~280 | 资金曲线 + 交易记录，滑点/佣金/印花税 |
| `core/risk_manager.py` | ~240 | 固定止盈止损 + 移动止损 + 涨跌停 |
| `core/reporter.py` | ~260 | CSV 输出、Matplotlib 对比图 |
| `core/metrics.py` | ~190 | 夏普/Sortino/Calmar/最大回撤/胜率 |
