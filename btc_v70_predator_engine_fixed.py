#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7.0 "掠食者"引擎 - 修复版

修复内容：
1. 添加数据平滑（EMA）
2. 修复Div_OI计算逻辑
3. 使用4小时LS数据
4. 优化参数配置

作者：Claude Code
日期：2026-01-08
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# Windows UTF-8修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class V70PredatorEngineFixed:
    """V7.0 "掠食者"引擎 - 修复版"""

    def __init__(self,
                 zscore_window=180,           # 180个4小时 = 30天
                 delta_ls_window=1,           # 1个4小时
                 delta_ls_accel_window=1,     # 1个4小时
                 score_threshold_level1=70,
                 score_threshold_level2=80,
                 score_threshold_level3=90,
                 liq_gravity_threshold=2.0,
                 vol_squeeze_percentile=10,
                 vol_squeeze_duration=3,
                 asymmetric_accel_factor_positive=1.2,
                 asymmetric_accel_factor_negative=0.8,
                 ema_span=5,                   # 新增：EMA平滑参数
                 data_frequency_hours=4):      # 4小时数据

        self.zscore_window = zscore_window
        self.delta_ls_window = delta_ls_window
        self.delta_ls_accel_window = delta_ls_accel_window
        self.score_threshold_level1 = score_threshold_level1
        self.score_threshold_level2 = score_threshold_level2
        self.score_threshold_level3 = score_threshold_level3
        self.liq_gravity_threshold = liq_gravity_threshold
        self.vol_squeeze_percentile = vol_squeeze_percentile
        self.vol_squeeze_duration = vol_squeeze_duration
        self.asymmetric_accel_factor_positive = asymmetric_accel_factor_positive
        self.asymmetric_accel_factor_negative = asymmetric_accel_factor_negative
        self.ema_span = ema_span
        self.data_frequency_hours = data_frequency_hours

        self.history_df = pd.DataFrame()
        self.vol_squeeze_counter = 0

    def _calculate_robust_zscore(self, series, window):
        """鲁棒Z-Score：(x - Median) / MAD"""
        if len(series) < window:
            return pd.Series([np.nan] * len(series), index=series.index)

        rolling_median = series.rolling(window=window, min_periods=1).median()
        rolling_mad = series.rolling(window=window, min_periods=1).apply(
            lambda x: np.median(np.abs(x - np.median(x))),
            raw=False
        )
        robust_zscore = (series - rolling_median) / rolling_mad.replace(0, np.nan)
        return robust_zscore

    def _calculate_ema_smooth(self, series, span=None):
        """EMA平滑（新增）"""
        if span is None:
            span = self.ema_span
        return series.ewm(span=span, adjust=False).mean()

    def _calculate_atr(self, df, atr_period=14):
        """ATR计算"""
        high = df["最高价"]
        low = df["最低价"]
        close = df["收盘价"]
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=atr_period, adjust=False).mean()
        return atr

    def _calculate_delta_ls_acceleration(self, ls_series):
        """
        计算二阶导数（修复版：添加平滑）

        流程：
        1. EMA平滑LS数据
        2. 计算一阶导数（速度）
        3. 计算二阶导数（加速度）
        4. 应用非对称权重
        """
        # 步骤1：EMA平滑
        ls_smooth = self._calculate_ema_smooth(ls_series)

        # 步骤2：一阶导数
        delta_ls = ls_smooth.diff(self.delta_ls_window).fillna(0)

        # 步骤3：二阶导数
        delta2_ls = delta_ls.diff(self.delta_ls_accel_window).fillna(0)

        # 步骤4：非对称权重
        weighted_delta2_ls = delta2_ls.apply(
            lambda x: x * self.asymmetric_accel_factor_positive if x > 0
            else x * self.asymmetric_accel_factor_negative
        )

        return weighted_delta2_ls

    def _calculate_div_oi(self, oi_series, price_series, window):
        """
        计算持仓/价格背离（修复版）

        逻辑：
        - Z_OI > 2.0 且 |价格变化| < 1% → 背离（主力在对冲）
        """
        z_oi = self._calculate_robust_zscore(oi_series, window)
        price_change_pct = price_series.pct_change() * 100

        # 背离信号：OI激增但价格平稳
        div_oi_signal = (z_oi > 2.0) & (abs(price_change_pct) < 1.0)

        # 转换为数值：True=1, False=0
        div_oi_score = div_oi_signal.astype(float)

        return div_oi_score

    def update_data(self, new_data_point: pd.Series):
        """添加新数据点"""
        if self.history_df.empty:
            self.history_df = pd.DataFrame([new_data_point])
        else:
            self.history_df = pd.concat([self.history_df, pd.DataFrame([new_data_point])],
                                       ignore_index=True)

        # 保持必要的历史长度
        max_length = self.zscore_window + self.delta_ls_window + self.delta_ls_accel_window + 100
        self.history_df = self.history_df.tail(max_length)
        self.history_df.index = pd.to_datetime(self.history_df["日期"])

    def get_predator_alert(self) -> dict:
        """生成V7.0预警信号"""
        if len(self.history_df) < self.zscore_window:
            return {"level": "NO_SIGNAL", "pulse_score": 0, "direction": "UNKNOWN",
                   "details": {"description": "Insufficient data", "current_price": 0, "ls_ratio": 0}}

        current_df = self.history_df.copy()

        # 1. 计算Z-Scores
        current_df["Z_Liq"] = self._calculate_robust_zscore(
            current_df["清算量(美元)"], self.zscore_window
        )
        current_df["Z_Vol"] = self._calculate_robust_zscore(
            current_df["成交量(BTC)"], self.zscore_window
        )
        current_df["Z_OI"] = self._calculate_robust_zscore(
            current_df["持仓量(OI-百万)"], self.zscore_window
        )

        # 2. 计算Div_OI（修复版）
        current_df["Z_DivOI"] = self._calculate_div_oi(
            current_df["持仓量(OI-百万)"],
            current_df["收盘价"],
            self.zscore_window
        )

        # 3. 计算加权二阶导数（修复版：添加平滑）
        current_df["Weighted_Delta2_LS"] = self._calculate_delta_ls_acceleration(
            current_df["多空比(LS)"]
        )

        # 获取最新值
        latest = current_df.iloc[-1]
        z_liq = latest["Z_Liq"]
        z_vol = latest["Z_Vol"]
        z_oi = latest["Z_OI"]
        z_div_oi = latest["Z_DivOI"]
        weighted_delta2_ls = latest["Weighted_Delta2_LS"]
        current_atr = self._calculate_atr(current_df).iloc[-1]

        # 处理NaN
        if pd.isna(z_liq) or pd.isna(z_vol) or pd.isna(z_oi) or \
           pd.isna(z_div_oi) or pd.isna(weighted_delta2_ls) or pd.isna(current_atr):
            return {"level": "NO_SIGNAL", "pulse_score": 0, "direction": "UNKNOWN",
                   "details": {"description": "Insufficient data for all factors", "current_price": 0, "ls_ratio": 0}}

        # 4. 计算Pulse Score
        pulse_score = (
            abs(z_liq) * 0.45 +
            abs(weighted_delta2_ls) * 0.35 +
            abs(z_vol) * 0.10 +
            abs(z_div_oi) * 0.10
        )
        pulse_score = min(pulse_score * 10, 100)

        # 5. 确定方向
        direction = "UNKNOWN"
        if weighted_delta2_ls > 0 and z_liq > 0:
            direction = "SHORT"
        elif weighted_delta2_ls < 0 and z_liq < 0:
            direction = "LONG"

        # 6. 应用过滤器
        # 6.1 引力位过滤器
        liq_gravity_filter_active = False
        if abs(z_liq) < self.liq_gravity_threshold and pulse_score >= self.score_threshold_level3:
            pulse_score -= 10
            liq_gravity_filter_active = True

        # 6.2 ATR静默模式
        atr_series = self._calculate_atr(current_df)
        if len(atr_series) >= self.zscore_window:
            # 使用百分位计算ATR分位数
            atr_percentile = atr_series.iloc[-1] / atr_series.max() * 100

            if atr_percentile < self.vol_squeeze_percentile:
                self.vol_squeeze_counter += 1
            else:
                self.vol_squeeze_counter = 0

            if self.vol_squeeze_counter >= self.vol_squeeze_duration:
                if pulse_score >= self.score_threshold_level2:
                    pulse_score -= 15
                    print(f"[FILTER] Volatility Squeeze active. Downgrading by 15. New score: {pulse_score:.2f}")

        # 7. 确定预警等级
        alert_level = "NO_SIGNAL"
        details_desc = f"Pulse: {pulse_score:.2f}, Dir: {direction}, Z_Liq: {z_liq:.2f}, Δ²LS: {weighted_delta2_ls:.4f}"

        if pulse_score >= self.score_threshold_level3:
            alert_level = "LEVEL 3 (坍塌)"
            details_desc += ", All factors Z > 3.0 (resonance)"
        elif pulse_score >= self.score_threshold_level2:
            alert_level = "LEVEL 2 (临界)"
            details_desc += ", Z_Liq > 2.5 & Accel > 45°"
        elif pulse_score >= self.score_threshold_level1:
            alert_level = "LEVEL 1 (监视)"
            details_desc += ", Z_Liq > 1.5 & Accel Positive"

        if liq_gravity_filter_active:
            details_desc += " [Liq Gravity Filter Applied]"

        # 返回字典格式的details
        details_dict = {
            "description": details_desc,
            "current_price": latest["收盘价"],
            "ls_ratio": latest["多空比(LS)"],
            "delta2_ls": weighted_delta2_ls,
            "z_liq": z_liq,
            "z_vol": z_vol,
            "z_div_oi": z_div_oi
        }

        return {
            "level": alert_level,
            "pulse_score": pulse_score,
            "direction": direction,
            "details": details_dict
        }


# ==================== 示例使用 ====================
if __name__ == "__main__":
    print("="*80)
    print("V7.0 Predator Engine - 修复版测试")
    print("="*80)
    print()

    # 加载历史数据
    try:
        df_history = pd.read_csv("btc_daily_ohlcv_2years.csv")
        df_history.columns = [c.strip().replace("\ufeff", "") for c in df_history.columns]
        df_history["日期"] = pd.to_datetime(df_history["日期"])
        df_history = df_history.sort_values("日期")

        print(f"✅ 数据加载成功: {len(df_history)} 天")
        print(f"   时间范围: {df_history['日期'].min()} ~ {df_history['日期'].max()}")
        print()

    except FileNotFoundError:
        print("❌ 数据文件未找到")
        print("   请确保文件存在: 测试/2026.1.6/btc_daily_ohlcv_2years.csv")
        exit()

    # 创建引擎（使用4小时配置，但数据是日线）
    engine = V70PredatorEngineFixed(
        zscore_window=30,              # 30天（日线数据）
        delta_ls_window=1,              # 1天
        delta_ls_accel_window=1,        # 1天
        ema_span=5,                     # EMA平滑
        data_frequency_hours=24         # 日线
    )

    # 运行回测
    alerts = []
    for i in range(len(df_history)):
        engine.update_data(df_history.iloc[i])
        alert = engine.get_predator_alert()

        if alert["level"] != "NO_SIGNAL":
            alerts.append({
                "date": df_history.iloc[i]["日期"],
                "price": df_history.iloc[i]["收盘价"],
                **alert
            })

    print(f"="*80)
    print(f"V7.0预警结果（日线数据，简化版）")
    print(f"="*80)
    print()
    print(f"总预警次数: {len(alerts)}")
    print()

    # 按等级分组
    level1 = [a for a in alerts if "LEVEL 1" in a["level"]]
    level2 = [a for a in alerts if "LEVEL 2" in a["level"]]
    level3 = [a for a in alerts if "LEVEL 3" in a["level"]]

    print(f"LEVEL 1 (监视): {len(level1)} 次")
    print(f"LEVEL 2 (临界): {len(level2)} 次")
    print(f"LEVEL 3 (坍塌): {len(level3)} 次")
    print()

    # 显示最新预警
    if len(alerts) > 0:
        print(f"最新10次预警:")
        print(f"-"*80)
        for alert in alerts[-10:]:
            print(f"{alert['date'].strftime('%Y-%m-%d')} | {alert['level']} | "
                 f"Score: {alert['pulse_score']:.2f} | {alert['direction']} | "
                 f"${alert['price']:,.2f}")
            print(f"  {alert['details']}")

    print()
    print(f"="*80)
    print(f"注意：此为日线数据简化版，完整V7.0需要4小时/15分钟LS数据")
    print(f"="*80)
