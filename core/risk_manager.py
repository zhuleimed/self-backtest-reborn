"""
风险管理模块 (RiskManager)

职责：
  1. 涨跌停限制处理（科创板±20%、北交所±30%、主板±10%）
  2. 止盈止损策略（固定止损、百分比止盈、回落止盈）
  3. 停牌日处理
"""

from typing import Dict, Optional, Tuple

import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .log_utils import get_logger

logger = get_logger(__name__)


class RiskManager:
    """
    风控管理器：对已生成 pos 信号的 DataFrame 施加风控规则。
    """

    # 各板块涨跌停限制
    LIMIT_RULES = {
        'kcb': (1.20, 0.80),      # 科创板 688 ±20%
        'bj': (1.30, 0.70),       # 北交所 43/83/87/88 ±30%
        'default': (1.10, 0.90),  # 主板 ±10%
    }

    def __init__(self):
        # 风控信号列
        self._stop_col = 'stop_signal'  # -1=止损, -2=止盈, -3=策略卖出

    # ------------------------------------------------------------------
    # 涨跌停限制
    # ------------------------------------------------------------------

    @staticmethod
    def get_limit_rules(stock_code: str) -> Tuple[float, float]:
        """根据股票代码确定涨跌停幅度"""
        if stock_code.startswith('688'):
            return RiskManager.LIMIT_RULES['kcb']
        elif stock_code.startswith(('430', '830', '870', '880')):
            return RiskManager.LIMIT_RULES['bj']
        return RiskManager.LIMIT_RULES['default']

    def apply_limit_up_down(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        涨停无法买入、跌停无法卖出的处理。

        逻辑：
          - 涨停开盘（open >= prev_close * up_limit）且拟买入 → pos 置 None
          - 跌停开盘（open <= prev_close * down_limit）且拟卖出 → pos 置 None
          - None 用前值前向填充
        """
        result = data.copy()
        stock_code = result['stock_code'].iloc[0]
        up_limit, down_limit = self.get_limit_rules(stock_code)

        prev_close = result['close'].shift(1)

        cannot_buy = result['open'] >= prev_close * up_limit
        result.loc[cannot_buy & (result['pos'] == 1), 'pos'] = None

        cannot_sell = result['open'] <= prev_close * down_limit
        result.loc[cannot_sell & (result['pos'] == 0), 'pos'] = None

        result['pos'] = result['pos'].ffill()
        return result

    # ------------------------------------------------------------------
    # 止盈止损
    # ------------------------------------------------------------------

    def apply_stop_strategy(self,
                            data: pd.DataFrame,
                            signal_name: str,
                            stop_loss_pct: float = 0.05,
                            stop_profit_pct: float = 0.20,
                            drawdown_pct: float = 0.03) -> pd.DataFrame:
        """
        参数化止盈止损策略。

        Parameters
        ----------
        data : pd.DataFrame
            必须包含 pos, {signal_name}_signal, open, high, volume 列。
        signal_name : str
            信号名称，用于定位信号列 {signal_name}_signal
        stop_loss_pct : float
            止损比例（0.05 = 5%）
        stop_profit_pct : float
            止盈触发比例（0.20 = 20%）
        drawdown_pct : float
            从最高点回落止盈比例（0.03 = 3%）

        Returns
        -------
        pd.DataFrame
            新增列：stop_signal, buy_price, highest_price, position_status
        """
        result = data.copy()
        signal_col = f'{signal_name}_signal'

        # 初始化
        result[self._stop_col] = 0
        result['buy_price'] = np.nan
        result['highest_price'] = np.nan
        result['position_status'] = 0

        stop_loss = 1 - stop_loss_pct
        stop_profit = 1 + stop_profit_pct
        drawdown = 1 - drawdown_pct

        in_position = False
        curr_buy_price = np.nan
        curr_max_price = np.nan

        for i in range(len(result)):
            # 停牌日保持状态
            if result.at[i, 'volume'] == 0:
                if in_position:
                    result.at[i, 'buy_price'] = curr_buy_price
                    result.at[i, 'highest_price'] = curr_max_price
                    result.at[i, 'position_status'] = 1
                continue

            if not in_position:
                if result.at[i, signal_col] == 1:
                    curr_buy_price = result.at[i, 'open']
                    curr_max_price = curr_buy_price
                    in_position = True
                    result.at[i, 'buy_price'] = curr_buy_price
                    result.at[i, 'highest_price'] = curr_max_price
                    result.at[i, 'position_status'] = 1
            else:
                # 更新最高价
                curr_max_price = max(curr_max_price, result.at[i, 'high'])
                result.at[i, 'highest_price'] = curr_max_price
                result.at[i, 'position_status'] = 1
                open_price = result.at[i, 'open']

                # 止损
                if open_price < curr_buy_price * stop_loss:
                    result.at[i, self._stop_col] = -1
                    in_position = False
                    result.at[i, 'position_status'] = 0
                    result.at[i, 'pos'] = 0
                    continue

                # 止盈（最高价达到目标后回落）
                if curr_max_price >= curr_buy_price * stop_profit:
                    if open_price < curr_max_price * drawdown:
                        result.at[i, self._stop_col] = -2
                        in_position = False
                        result.at[i, 'position_status'] = 0
                        result.at[i, 'pos'] = 0
                        continue

                # 原始策略卖出
                if result.at[i, signal_col] == -1:
                    result.at[i, self._stop_col] = -3
                    in_position = False
                    result.at[i, 'position_status'] = 0
                    result.at[i, 'pos'] = 0

            if not in_position and result.at[i, signal_col] == 1:
                pass  # 重新买入由下一循环处理

        return result

    # ------------------------------------------------------------------
    # 停牌日处理（简化版：直接在 equity_curve 模块中处理）
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 移动止盈止损（trailing stop）
    # ------------------------------------------------------------------

    def apply_trailing_stop(self,
                            data: pd.DataFrame,
                            signal_name: str,
                            trailing_stop_pct: float = 0.07,
                            trailing_profit_pct: float = 0.15) -> pd.DataFrame:
        """
        移动止盈止损策略。

        与固定止盈止损的区别：
          - 固定止损：以买入价为基准，跌 X% 止损
          - 移动止损：以**持仓期间最高价**为基准，从最高价跌 X% 止损
          适用于强势股，让利润奔跑的同时锁定回撤。

        Parameters
        ----------
        trailing_stop_pct : float
            移动止损比例：从最高价回落 X% 时卖出（默认 7%）
        trailing_profit_pct : float
            移动止盈触发比例：涨幅超过 X% 后才激活移动止损（默认 15%）
        """
        result = data.copy()
        signal_col = f'{signal_name}_signal'

        # 停牌日沿用已有 stop_signal
        result['stop_signal'] = result.get('stop_signal', 0)

        in_position = False
        entry_price = 0.0
        peak_price = 0.0
        trailing_activated = False

        for i in range(len(result)):
            if result.at[i, 'volume'] == 0:
                continue

            if not in_position:
                if result.at[i, signal_col] == 1:
                    entry_price = result.at[i, 'open']
                    peak_price = entry_price
                    in_position = True
                    trailing_activated = False
            else:
                # 更新最高价
                peak_price = max(peak_price, result.at[i, 'high'])

                # 检查是否达到移动止盈激活条件
                if not trailing_activated:
                    gain = (peak_price - entry_price) / entry_price
                    if gain >= trailing_profit_pct:
                        trailing_activated = True

                # 移动止损检查（从最高价回落）
                if trailing_activated:
                    drawdown = (peak_price - result.at[i, 'open']) / peak_price
                    if drawdown >= trailing_stop_pct:
                        result.at[i, 'stop_signal'] = -1  # 复用止损标记
                        result.at[i, 'pos'] = 0
                        in_position = False
                        continue

                # 原有策略卖出信号仍然有效
                if result.at[i, signal_col] == -1:
                    result.at[i, 'stop_signal'] = -3
                    result.at[i, 'pos'] = 0
                    in_position = False

        return result

    # ------------------------------------------------------------------
    # 大盘环境过滤
    # ------------------------------------------------------------------

    @staticmethod
    def check_market_condition(index_data: pd.DataFrame,
                                index_code: str = 'hushen300',
                                ma_period: int = 20,
                                drop_threshold: float = -0.03) -> Tuple[bool, str]:
        """
        检查大盘环境是否适合开仓。

        基于指数日线数据判断：
          - 指数在 N 日均线之上 → 多头市场
          - 指数近 5 日跌幅超过 threshold → 空头/调整市场

        Parameters
        ----------
        index_data : pd.DataFrame
            指数日线数据（含 close, pctChg 列）
        ma_period : int
            均线周期（默认 20 日）
        drop_threshold : float
            近 5 日跌幅阈值（默认 -3%）

        Returns
        -------
        (is_favorable, reason)
            is_favorable: True 表示适合开仓
            reason: 判断理由描述
        """
        if index_data is None or len(index_data) < ma_period + 5:
            return True, '指数数据不足，默认允许开仓'

        close = index_data['close'].values
        ma = pd.Series(close).rolling(ma_period).mean().values

        latest_close = close[-1]
        latest_ma = ma[-1]

        # 条件 1：价格在均线之上
        above_ma = latest_close > latest_ma

        # 条件 2：近 5 日跌幅
        if len(close) >= 6:
            recent_drop = (close[-1] - close[-6]) / close[-6]
        else:
            recent_drop = 0.0

        no_crash = recent_drop > drop_threshold

        # 综合判断
        if above_ma and no_crash:
            return True, '大盘环境 OK（多头 + 无急跌）'
        elif not above_ma and no_crash:
            return False, f'大盘偏空：指数 {latest_close:.0f} < {ma_period}日线 {latest_ma:.0f}'
        elif above_ma and not no_crash:
            return False, f'大盘急跌：近 5 日跌幅 {recent_drop:.1%} < {drop_threshold:.0%}'
        else:
            return False, f'大盘恶劣：指数破位 + 急跌 {recent_drop:.1%}'

    # ------------------------------------------------------------------
    # 大盘环境过滤（应用于股票数据）
    # ------------------------------------------------------------------

    def apply_market_filter(self,
                            data: pd.DataFrame,
                            index_data: pd.DataFrame,
                            index_code: str = 'hushen300',
                            ma_period: int = 20,
                            drop_threshold: float = -0.03) -> pd.DataFrame:
        """
        对股票数据施加大盘环境过滤。
        大盘环境不佳时，将所有买入信号（pos=1）置为 0（不开仓）。

        Returns
        -------
        pd.DataFrame
            新增列 market_ok（bool）表示当日是否允许开仓
        """
        result = data.copy()
        is_favorable, reason = self.check_market_condition(
            index_data, index_code, ma_period, drop_threshold
        )

        # 将大盘判断结果记录到每日数据中
        result['market_ok'] = is_favorable

        if not is_favorable:
            logger.warning(f'大盘过滤: {reason}')
            # 将所有持仓信号置为空仓
            result.loc[result['pos'] == 1, 'pos'] = 0
            result['pos'] = result['pos'].ffill().fillna(0)
        else:
            logger.info(f'大盘过滤: {reason}')

        return result

    @staticmethod
    def is_suspended(row: pd.Series) -> bool:
        """判断当日是否停牌"""
        return row['open'] == 0 or row['volume'] == 0
