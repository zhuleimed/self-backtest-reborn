"""
ARBR 情绪指标信号

基于 AR（人气指标）和 BR（意愿指标）的组合信号：
  AR 上穿 150（恐慌超卖区） + BR 下穿 50（极端悲观）+ 成交量放大 → 买入
  （"顶级诱空信号"策略）
"""

import numpy as np
import pandas as pd

from core.signal_engine import BaseSignal


class ARBRSignal(BaseSignal):
    """ARBR 情绪指标信号"""

    name = 'ARBR'

    def __init__(self, period: int = 26, ar_threshold: float = 150.0,
                 br_threshold: float = 50.0, volume_ratio: float = 1.5,
                 sync_days: int = 3):
        self.params = {
            'period': period,
            'ar_threshold': ar_threshold,
            'br_threshold': br_threshold,
            'volume_ratio': volume_ratio,
            'sync_days': sync_days,
        }

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        p = self.params

        # 1. 计算 AR
        numerator = (df['high'] - df['open']).rolling(p['period']).sum()
        denominator = (df['open'] - df['low']).rolling(p['period']).sum()
        denominator[denominator == 0] = 0.001
        df['AR'] = (numerator / denominator) * 100

        # 2. 计算 BR
        prev_close = df['close'].shift(1)
        h_minus_pc = df['high'] - prev_close
        h_minus_pc[h_minus_pc < 0] = 0
        br_num = h_minus_pc.rolling(p['period']).sum()

        pc_minus_l = prev_close - df['low']
        pc_minus_l[pc_minus_l < 0] = 0
        br_den = pc_minus_l.rolling(p['period']).sum()
        br_den[br_den == 0] = 0.001
        df['BR'] = (br_num / br_den) * 100

        # 3. 均线
        df['MA60'] = df['close'].rolling(60).mean()
        df['MA20'] = df['close'].rolling(20).mean()

        # 4. 信号
        df['ARBR_signal'] = 0

        for i in range(1, len(df)):
            # AR 上穿阈值
            ar_cross = (df['AR'].iloc[i] > p['ar_threshold']
                        and df['AR'].iloc[i - 1] <= p['ar_threshold'])
            # BR 下穿阈值
            br_cross = (df['BR'].iloc[i] < p['br_threshold']
                        and df['BR'].iloc[i - 1] >= p['br_threshold'])

            # 检查最近 sync_days 日内是否两信号同步
            ar_cross_idx = i if ar_cross else None
            br_cross_idx = i if br_cross else None

            # 回看找到最近的交叉点
            for j in range(max(0, i - p['sync_days']), i + 1):
                if ar_cross_idx is None and j > 0:
                    if (df['AR'].iloc[j] > p['ar_threshold']
                            and df['AR'].iloc[j - 1] <= p['ar_threshold']):
                        ar_cross_idx = j
                if br_cross_idx is None and j > 0:
                    if (df['BR'].iloc[j] < p['br_threshold']
                            and df['BR'].iloc[j - 1] >= p['br_threshold']):
                        br_cross_idx = j

            if ar_cross_idx is not None and br_cross_idx is not None:
                time_diff = abs(ar_cross_idx - br_cross_idx)
                if time_diff <= p['sync_days']:
                    # 成交量确认
                    vol_ok = False
                    if i > 0 and df['volume'].iloc[i - 1] > 0:
                        vol_ok = (df['volume'].iloc[i]
                                  >= df['volume'].iloc[i - 1] * p['volume_ratio'])

                    # 价格位置：处于 60 日线下方（相对低位）
                    price_low = df['close'].iloc[i] < df['MA60'].iloc[i]

                    if vol_ok and price_low:
                        df.loc[df.index[i], 'ARBR_signal'] = 1

            # 卖出信号：AR 从高位回落 + BR 从低位反弹
            ar_high = df['AR'].iloc[i] > 120
            br_rebound = (df['BR'].iloc[i] > 80
                          and df['BR'].iloc[i - 1] <= 80)
            if ar_high and br_rebound:
                df.loc[df.index[i], 'ARBR_signal'] = -1

        return df
