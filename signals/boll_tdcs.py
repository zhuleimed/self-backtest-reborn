"""
布林带参数调优信号 (BOLL TDCS)

基于布林带多维度判断的"短线高手 BOLL 密码"策略：
  - 买入：价格在布林带下轨附近 + 收口后开口向上 + 成交量配合
  - 卖出：价格突破上轨 + 乖离过大 + 成交量萎缩

可使用 `use_all_signals=True` 开启全部信号判断。
"""

import numpy as np
import pandas as pd

from core.signal_engine import BaseSignal


class BOLLTDCSignal(BaseSignal):
    """布林带参数调优信号"""

    name = 'BOLL_TDCS'

    def __init__(self, period: int = 20, std_multiplier: float = 2.0,
                 use_all_signals: bool = True):
        self.params = {
            'period': period,
            'std_multiplier': std_multiplier,
            'use_all_signals': use_all_signals,
        }

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        p = self.params

        # 1. 布林带
        mid = df['close'].rolling(p['period']).mean()
        std = df['close'].rolling(p['period']).std(ddof=0)
        df['BOLL_MID'] = mid
        df['BOLL_UPPER'] = mid + p['std_multiplier'] * std
        df['BOLL_LOWER'] = mid - p['std_multiplier'] * std
        df['BOLL_BANDWIDTH'] = ((df['BOLL_UPPER'] - df['BOLL_LOWER']) / df['BOLL_MID']) * 100

        # 2. 均线
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA10'] = df['close'].rolling(10).mean()
        df['MA20'] = df['close'].rolling(20).mean()
        df['MA60'] = df['close'].rolling(60).mean()

        # 3. 成交量均线
        df['VOL_MA5'] = df['volume'].rolling(5).mean()

        # 4. MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_HIST'] = df['DIF'] - df['DEA']

        # 5. RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['RSI'] = 100 - (100 / (1 + rs))

        # 6. 信号
        df['BOLL_TDCS_signal'] = 0
        min_period = max(p['period'], 60)

        for i in range(min_period, len(df)):
            # 计算价格位置
            pos = self._price_position(df, i)
            vol_active = self._volume_active(df, i)

            # ---- 买入 ----
            buy_cond = (
                # 价格在下轨附近或触及下轨
                (pos['near_lower'] or pos['below_lower'])
                and
                # 收口后中轨走平或向上
                (self._mid_trend(df, i) in ('up', 'flat'))
                and
                # 成交量活跃
                vol_active
            )

            if p['use_all_signals']:
                buy_cond = (
                    buy_cond
                    and self._macd_bullish(df, i)
                    and df['RSI'].iloc[i] < 50
                    and df['close'].iloc[i] < df['MA60'].iloc[i] * 1.1
                )

            if buy_cond:
                df.loc[df.index[i], 'BOLL_TDCS_signal'] = 1
                continue

            # ---- 卖出 ----
            sell_cond = (
                # 价格突破上轨
                pos['above_upper']
                and
                # 成交量萎缩
                df['volume'].iloc[i] < df['VOL_MA5'].iloc[i] * 0.8
            )

            if p['use_all_signals']:
                sell_cond = (
                    sell_cond
                    or (
                        pos['near_upper']
                        and df['RSI'].iloc[i] > 70
                        and not vol_active
                    )
                )

            if sell_cond:
                df.loc[df.index[i], 'BOLL_TDCS_signal'] = -1

        return df

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _price_position(df, i):
        """判断价格相对于布林带的位置"""
        close = df['close'].iloc[i]
        upper = df['BOLL_UPPER'].iloc[i]
        mid = df['BOLL_MID'].iloc[i]
        lower = df['BOLL_LOWER'].iloc[i]

        total_range = upper - lower
        pos_pct = ((close - lower) / total_range * 100) if total_range != 0 else 50

        return {
            'above_upper': close > upper,
            'near_upper': lower < close < upper and pos_pct > 80,
            'near_mid': lower < close < upper and 40 <= pos_pct <= 60,
            'near_lower': lower < close < upper and pos_pct < 20,
            'below_lower': close < lower,
            'pct': pos_pct,
        }

    @staticmethod
    def _volume_active(df, i, lookback=5):
        """成交量是否活跃（当日 > 均量 * 1.2）"""
        if i < lookback:
            return False
        avg_vol = df['volume'].iloc[i - lookback:i].mean()
        return df['volume'].iloc[i] > avg_vol * 1.2

    @staticmethod
    def _mid_trend(df, i, lookback=3):
        """判断中轨趋势方向"""
        if i < lookback:
            return 'flat'
        vals = df['BOLL_MID'].iloc[i - lookback:i + 1].values
        if all(vals[j + 1] > vals[j] for j in range(lookback)):
            return 'up'
        if all(vals[j + 1] < vals[j] for j in range(lookback)):
            return 'down'
        return 'flat'

    @staticmethod
    def _macd_bullish(df, i):
        """MACD 是否偏多"""
        if i < 1:
            return False
        # DIF 上穿 DEA 或 DIF 在 DEA 上方
        return (df['DIF'].iloc[i] > df['DEA'].iloc[i]
                and df['MACD_HIST'].iloc[i] > 0)
