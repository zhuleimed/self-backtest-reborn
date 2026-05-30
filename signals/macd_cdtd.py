"""
MACD 顶底背离信号 (MACD CDTD)

基于 MACD 指标柱状图面积和高度对比的顶底背离策略：
  - 底背离（买入）：绿柱群面积递减 + 前一波高度 3 倍于后一波 + MA5 上穿 MA10
  - 顶背离（卖出）：红柱群呈"中间凹陷"形态 + 前高后低 + 放量长阴
"""

import numpy as np
import pandas as pd

from core.signal_engine import BaseSignal


class MACDCDTDSignal(BaseSignal):
    """MACD 顶底背离信号"""

    name = 'MACD_CDTD'

    def __init__(self, fast_period: int = 12, slow_period: int = 26,
                 signal_period: int = 9, ma_fast: int = 5, ma_slow: int = 10):
        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'ma_fast': ma_fast,
            'ma_slow': ma_slow,
        }

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        # 1. MACD 计算
        ema_fast = df['close'].ewm(span=self.params['fast_period'], adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.params['slow_period'], adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=self.params['signal_period'], adjust=False).mean()
        macd_val = 2 * (dif - dea)

        df['DIF'] = dif
        df['DEA'] = dea
        df['MACD'] = macd_val

        # 2. 均线
        ma_fast_val = df['close'].rolling(self.params['ma_fast']).mean()
        ma_slow_val = df['close'].rolling(self.params['ma_slow']).mean()
        df['MA5'] = ma_fast_val
        df['MA10'] = ma_slow_val

        # 3. 识别 MACD 红绿柱区域
        areas = self._find_macd_areas(macd_val.values)

        df['MACD_CDTD_signal'] = 0

        if len(areas) < 3:
            return df

        latest_idx = len(df) - 1

        # 找最近的两个绿柱区（买入信号）
        green_areas = [a for a in areas if a['type'] == 'green']
        latest_green = green_areas[-1] if len(green_areas) >= 1 else None
        prev_green = green_areas[-2] if len(green_areas) >= 2 else None

        # 找最近的红柱区（卖出信号）
        red_areas = [a for a in areas if a['type'] == 'red']
        latest_red = red_areas[-1] if len(red_areas) >= 1 else None

        # ---- 买入信号：底背离 ----
        if latest_green and prev_green:
            latest_heights = [abs(v) for v in df['MACD'].iloc[
                latest_green['start_idx']:latest_green['end_idx'] + 1]]
            prev_heights = [abs(v) for v in df['MACD'].iloc[
                prev_green['start_idx']:prev_green['end_idx'] + 1]]

            c1 = False
            if len(prev_heights) >= 3:
                third_smallest = sorted(prev_heights)[2]
                c1 = all(h < third_smallest for h in latest_heights)

            c2 = (max(prev_heights) > max(latest_heights) * 3) if latest_heights and prev_heights else False

            c3 = False
            if len(latest_heights) >= 2:
                second_last_idx = latest_green['end_idx'] - 1
                if second_last_idx >= 1:
                    c3 = (df['MA5'].iloc[second_last_idx - 1] < df['MA10'].iloc[second_last_idx - 1]
                          and df['MA5'].iloc[second_last_idx] >= df['MA10'].iloc[second_last_idx])

            c4 = df['close'].iloc[-1] > df['MA5'].iloc[-1]

            c5 = False
            if len(df) >= 5:
                c5 = any(df['volume'].iloc[-1] > df['volume'].iloc[-i] for i in [2, 3, 4])

            if c1 and c2 and c3 and c4 and c5:
                df.loc[latest_idx, 'MACD_CDTD_signal'] = 1

        # ---- 卖出信号：顶背离 ----
        if latest_red:
            red_macd = df['MACD'].iloc[latest_red['start_idx']:latest_red['end_idx'] + 1].values
            rlen = len(red_macd)
            if rlen >= 5:
                mid_s = int(rlen * 0.3)
                mid_e = int(rlen * 0.7)
                if mid_e - mid_s < 1:
                    mid_s, mid_e = int(rlen * 0.4), int(rlen * 0.6)

                front = red_macd[:mid_s]
                middle = red_macd[mid_s:mid_e]
                back = red_macd[mid_e:]

                rc1 = (len(front) > 0 and len(middle) > 0 and len(back) > 0
                       and all(h < front[-1] and h < back[0] for h in middle))

                rc2 = (len(front) > 0 and len(back) > 0
                       and max(front) > max(back))

                rc3 = False
                if len(back) > 0:
                    max_back_idx = latest_red['start_idx'] + mid_s + mid_e + np.argmax(back)
                    if 0 < max_back_idx < len(df):
                        vol_cond = df['volume'].iloc[max_back_idx] >= df['volume'].iloc[max_back_idx - 1] * 2
                        kline_cond = (df['close'].iloc[max_back_idx] < df['open'].iloc[max_back_idx]
                                      and df['close'].iloc[max_back_idx] == df['low'].iloc[max_back_idx])
                        rc3 = vol_cond and kline_cond

                rc4 = False
                last_red_idx = latest_red['end_idx']
                if last_red_idx > 0 and last_red_idx == latest_idx:
                    rc4 = df['volume'].iloc[last_red_idx] < df['volume'].iloc[last_red_idx - 1]

                if rc1 and rc2 and rc3 and rc4:
                    df.loc[latest_idx, 'MACD_CDTD_signal'] = -1

        return df

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _find_macd_areas(macd_series):
        """识别 MACD 红绿柱区域"""
        areas = []
        current = None
        for i in range(len(macd_series)):
            if pd.isna(macd_series[i]):
                continue
            area_type = 'green' if macd_series[i] < 0 else 'red'
            if current is None:
                current = {'start_idx': i, 'type': area_type}
            elif current['type'] != area_type:
                current['end_idx'] = i - 1
                areas.append(current)
                current = {'start_idx': i, 'type': area_type}
        if current is not None:
            current['end_idx'] = len(macd_series) - 1
            areas.append(current)
        return areas
