---
name: data-loader
description: 数据加载技能——从本地 CSV 目录加载 A 股日线数据，清洗、校验、裁剪日期范围
user-invocable: false
allowed-tools:
  - "Read"
  - "Bash(python -c *)"
  - "Bash(ls *)"
---

# Data Loader Skill

加载股票日线数据并做标准化预处理。

## 输入
- `stock_codes`: 股票代码列表，如 `['000012', '000014']`
- `start_date`: 开始日期 `YYYY-MM-DD`
- `end_date`: 结束日期（可选，默认为最新）
- `data_dir`: CSV 数据目录（可选）

## 数据目录
数据位于 `/public/home/hpc/zhulei/superman/quant/data/input/`
格式：每只股票一个 CSV，文件名 `{stock_code}.csv`

## 执行步骤

1. **验证数据目录**：
   检查 `data_dir` 是否存在，确保有股票 CSV 文件。

2. **加载每只股票**：
   调用 `DataLoader.load_stock()` 加载每只股票，自动过滤：
   - ST 股（最近交易日 `isST == 1`）
   - 次新股（不足 240 个交易日）
   - 缺失列

3. **生成标准化输出**：
   返回包含以下列的 DataFrame：
   `date, open, high, low, close, volume, amount, pct_chg, cumulative_returns, stock_code`

## 输出
标准化的股票数据字典 `{stock_code: DataFrame}`，传递到下一个技能。
