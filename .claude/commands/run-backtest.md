---
description: 运行回测——执行量化策略回测流水线，生成绩效报告与图表
model: sonnet
allowed-tools:
  - AskUserQuestion
  - Agent
  - Skill
---

# Run Backtest Command

运行模块化量化回测框架，执行完整的回测流水线。

## 执行合约（不可协商）

你必须通过 `backtest-agent` 子代理来完成回测任务。禁止：
- 直接运行 `run_backtest.py` 脚本而不使用 Agent
- 在命令中自行拼装 Python 参数
- 跳过用户确认回测参数

## 工作流程

### Step 1: 询问用户回测参数

使用 AskUserQuestion 工具确认以下参数（如果用户已提供则跳过）：

1. **股票池**：哪些股票？预置方案还是自定义？
2. **时间范围**：开始日期？结束日期（默认到最新）？
3. **策略**：KAMA 还是其他信号？
4. **风控**：止盈止损比例？

### Step 2: 通过 Agent 执行回测

```
Agent(
  subagent_type="backtest-agent",
  description="Run backtest",
  prompt="使用 KAMA 策略回测 000012,000014，时间 2022-01-01 至今，止损5%止盈20%"
)
```

### Step 3: 呈现结果

回测完成后，解读关键绩效指标并展示收益曲线图。
