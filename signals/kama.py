"""
KAMA 自适应移动平均线信号

基于 Kaufman's Adaptive Moving Average (KAMA) 的买卖信号：
  - 上穿 KAMA → 买入信号 (1)
  - 下穿 KAMA → 卖出信号 (-1)
"""

import numpy as np
import pandas as pd

from core.signal_engine import BaseSignal


class KAMASignal(BaseSignal):
    """KAMA 自适应移动平均线信号"""

    name = 'KAMA'

    def __init__(self, n: int = 10, fast: int = 2, slow: int = 30):
        self.params = {'n': n, 'fast': fast, 'slow': slow}

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        close = df['close'].values
        length = len(close)

        n = self.params['n']
        fast = self.params['fast']
        slow = self.params['slow']

        # 向量化 KAMA 计算
        kama = np.full(length, np.nan)
        kama[n - 1] = close[:n].mean()

        fast_sc = 2.0 / (fast + 1)
        slow_sc = 2.0 / (slow + 1)

        for i in range(n, length):
            change = abs(close[i] - close[i - n])
            volatility = np.sum(np.abs(np.diff(close[i - n:i + 1])))
            er = change / volatility if volatility != 0 else 0
            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
            kama[i] = kama[i - 1] + sc * (close[i] - kama[i - 1])

        df['KAMA'] = kama

        # 信号生成
        prev_close = df['close'].shift(1)
        prev_kama = df['KAMA'].shift(1)

        buy_cond = (prev_close < prev_kama) & (df['close'] >= df['KAMA'])
        sell_cond = (prev_close > prev_kama) & (df['close'] <= df['KAMA'])

        df['KAMA_signal'] = 0
        df.loc[buy_cond, 'KAMA_signal'] = 1
        df.loc[sell_cond, 'KAMA_signal'] = -1

        return df
