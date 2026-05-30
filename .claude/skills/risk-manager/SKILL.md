---
name: risk-manager
description: 风控管理技能——对已有信号的股票数据施加涨跌停限制、止盈止损策略
user-invocable: false
allowed-tools:
  - "Read"
---

# Risk Manager Skill

对仓位信号施加风控规则，确保回测更贴近实际交易。

## 输入
- 含 `pos` 列和信号列的股票 DataFrame

## 风控规则

### 1. 涨跌停限制
根据股票代码自动判断板块：
- **688 (科创板)**: ±20%
- **43x/83x/87x/88x (北交所)**: ±30%
- **其他 (主板)**: ±10%

涨停日无法买入，跌停日无法卖出。

### 2. 止盈止损
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `stop_loss_pct` | 5% | 买入价下跌 X% 触发止损 |
| `stop_profit_pct` | 20% | 最高价达到买入价 X% 激活回落止盈 |
| `drawdown_pct` | 3% | 从最高点回落 X% 触发止盈 |

### 3. 停牌处理
停牌日保持原有仓位不变。

## 输出
新增列：
- `stop_signal`: -1=止损, -2=止盈, -3=策略卖出, 0=无
- `buy_price`: 买入价格
- `highest_price`: 持仓期间最高价
- `position_status`: 0=空仓, 1=持仓
