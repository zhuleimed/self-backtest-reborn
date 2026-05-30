---
name: signal-generator
description: 信号生成技能——对股票数据运用信号策略，生成买入/卖出信号并转化为仓位信号
user-invocable: false
allowed-tools:
  - "Read"
  - "Write"
  - "Edit"
---

# Signal Generator Skill

对已加载的股票数据应用信号策略，生成交易信号。

## 输入
- 上一技能输出的 `{stock_code: DataFrame}` 字典
- 信号策略名称与参数

## 策略系统

框架支持可插拔的策略类，每个策略继承 `BaseSignal`：

| 策略 | 类名 | 参数 |
|------|------|------|
| KAMA | `KAMASignal` | n, fast, slow |
| MACD 顶底背离 | `MACDCDTDSignal` | (开发中) |

## 执行步骤

1. **注册策略**：使用 `SignalEngine.register(strategy)` 注册
2. **生成信号**：调用 `SignalEngine.generate(data)` 对每只股票生成信号
3. **合成仓位**：引擎自动完成信号 → 仓位转换（pos = 0/1）

## 输出
DataFrame 新增列：
- `{name}_signal`: 原始信号（1=买入，-1=卖出，0=无操作）
- `pos`: 合成仓位（0=空仓，1=持仓）
- 辅助列（如指标值）
