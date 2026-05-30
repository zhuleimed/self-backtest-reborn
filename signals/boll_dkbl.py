"""
布林带带宽收口变盘信号 (BOLL DKBL)

基于 BOLL 布林带带宽比例尺收口 → 变盘前识别突破方向：
  - 买入：带宽收口 + 价格突破中轨向上 + 成交量放大 + 中轨向上
  - 卖出：带宽收口 + 价格跌破中轨向下 + 成交量放大 + 中轨向下
"""

import numpy as np
import pandas as pd

from core.signal_engine import BaseSignal


class BOLLDKBLSignal(BaseSignal):
    """布林带带宽收口变盘信号"""

    name = 'BOLL_DKBL'

    def __init__(self, period: int = 20, std_multiplier: float = 2.0,
                 lookback: int = 20, volume_ratio: float = 1.5,
                 bandwidth_percentile: float = 20.0):
        """
        Parameters
        ----------
        bandwidth_percentile : float
            带宽比例尺阈值百分位（最近 lookback 日中带宽小于此百分位视为收口）
        """
        self.params = {
            'period': period,
            'std_multiplier': std_multiplier,
            'lookback': lookback,
            'volume_ratio': volume_ratio,
            'bandwidth_percentile': bandwidth_percentile,
        }

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        p = self.params

        # 1. 布林带计算
        mid = df['close'].rolling(p['period']).mean()
        std = df['close'].rolling(p['period']).std()
        df['BOLL_MID'] = mid
        df['BOLL_UPPER'] = mid + p['std_multiplier'] * std
        df['BOLL_LOWER'] = mid - p['std_multiplier'] * std
        df['BOLL_BANDWIDTH'] = ((df['BOLL_UPPER'] - df['BOLL_LOWER']) / df['BOLL_MID']) * 100

        # 2. RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['RSI'] = 100 - (100 / (1 + rs))

        # 3. 成交量均线
        df['VOL_MA5'] = df['volume'].rolling(5).mean()

        # 4. 均线
        df['MA20'] = df['close'].rolling(20).mean()
        df['MA60'] = df['close'].rolling(60).mean()

        # 5. 信号
        df['BOLL_DKBL_signal'] = 0
        min_period = max(p['period'], p['lookback'])

        for i in range(min_period, len(df)):
            # 带宽在历史低位（收口状态）
            hist_bw = df['BOLL_BANDWIDTH'].iloc[i - p['lookback']:i + 1]
            pct_threshold = np.percentile(hist_bw, p['bandwidth_percentile'])
            is_narrow = df['BOLL_BANDWIDTH'].iloc[i] <= pct_threshold

            if not is_narrow:
                continue

            # ---- 买入条件 ----
            buy_cond = (
                # 价格突破中轨
                df['close'].iloc[i] > df['BOLL_MID'].iloc[i]
                and df['close'].iloc[i - 1] <= df['BOLL_MID'].iloc[i - 1]
                and
                # 成交量放大
                df['volume'].iloc[i] > df['VOL_MA5'].iloc[i] * p['volume_ratio']
                and
                # 中轨向上
                df['BOLL_MID'].iloc[i] > df['BOLL_MID'].iloc[i - 1]
                and
                # RSI 不超买
                df['RSI'].iloc[i] < 70
            )

            if buy_cond:
                df.loc[df.index[i], 'BOLL_DKBL_signal'] = 1
                continue

            # ---- 卖出条件 ----
            sell_cond = (
                # 价格跌破中轨
                df['close'].iloc[i] < df['BOLL_MID'].iloc[i]
                and df['close'].iloc[i - 1] >= df['BOLL_MID'].iloc[i - 1]
                and
                # 成交量放大
                df['volume'].iloc[i] > df['VOL_MA5'].iloc[i] * p['volume_ratio']
                and
                # 中轨向下
                df['BOLL_MID'].iloc[i] < df['BOLL_MID'].iloc[i - 1]
            )

            if sell_cond:
                df.loc[df.index[i], 'BOLL_DKBL_signal'] = -1

        return df
