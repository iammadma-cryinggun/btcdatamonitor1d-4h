#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
市场环境过滤器

功能：判断市场环境（牛市/熊市/震荡）
用途：过滤牛市阶段的做空预警

作者：Claude Code
日期：2026-01-08
"""

import pandas as pd
import numpy as np

class MarketFilter:
    """市场环境过滤器"""

    @staticmethod
    def check_market_environment(df, lookback=60):
        """
        判断市场环境：牛市/熊市/震荡

        指标：
        1. 60日价格趋势
        2. 60日成交量趋势
        3. LS Ratio趋势

        参数:
            df: 历史数据（需包含收盘价、成交量、多空比）
            lookback: 回溯天数（默认60天）

        返回:
            dict: {
                'environment': 'BULL' | 'BEAR' | 'NEUTRAL',
                'price_trend': float,      # 价格趋势%
                'vol_trend': float,        # 成交量趋势%
                'ls_trend': float,         # LS趋势%
                'confidence': str          # 置信度
            }
        """
        if len(df) < lookback:
            return {
                'environment': 'NEUTRAL',
                'price_trend': 0,
                'vol_trend': 0,
                'ls_trend': 0,
                'confidence': 'LOW',
                'reason': f'数据不足（{len(df)}天 < {lookback}天）'
            }

        recent = df.tail(lookback).copy()

        # 1. 价格趋势
        start_price = recent.iloc[0]['收盘价']
        end_price = recent.iloc[-1]['收盘价']
        price_trend = (end_price / start_price - 1) * 100

        # 2. 成交量趋势
        start_vol = recent.iloc[0]['成交量(BTC)']
        end_vol = recent.iloc[-1]['成交量(BTC)']
        vol_trend = (end_vol / start_vol - 1) * 100 if start_vol > 0 else 0

        # 3. LS Ratio趋势
        start_ls = recent.iloc[0]['多空比(LS)']
        end_ls = recent.iloc[-1]['多空比(LS)']
        ls_trend = (end_ls / start_ls - 1) * 100 if start_ls > 0 else 0

        # 判断市场环境
        environment = 'NEUTRAL'
        confidence = 'MEDIUM'
        reason = ''

        # 牛市判断（简化：只要价格涨就认为是牛市）
        if price_trend > 10:
            environment = 'BULL'
            if price_trend > 30:
                environment = 'STRONG_BULL'
                confidence = 'VERY_HIGH'
            else:
                confidence = 'HIGH'
            reason = f'价格上涨{price_trend:.1f}%'

        # 熊市判断
        elif price_trend < -5:
            environment = 'BEAR'
            if price_trend < -15:
                environment = 'STRONG_BEAR'
                confidence = 'VERY_HIGH'
            else:
                confidence = 'HIGH'
            reason = f'价格下跌{abs(price_trend):.1f}%'

        # 震荡（其他情况）
        else:
            environment = 'NEUTRAL'
            if abs(price_trend) < 5:
                confidence = 'HIGH'
                reason = f'价格平稳（{price_trend:+.1f}%）'
            else:
                confidence = 'MEDIUM'
                reason = f'价格震荡（{price_trend:+.1f}%）'

        return {
            'environment': environment,
            'price_trend': price_trend,
            'vol_trend': vol_trend,
            'ls_trend': ls_trend,
            'confidence': confidence,
            'reason': reason
        }

    @staticmethod
    def should_skip_short_alert(market_env):
        """
        判断是否应该跳过做空预警

        参数:
            market_env: check_market_environment()返回的结果

        返回:
            bool: True=跳过做空，False=执行做空
        """
        env = market_env['environment']

        # 牛市阶段跳过做空
        if env in ['BULL', 'STRONG_BULL']:
            return True

        # 熊市/震荡阶段执行做空
        else:
            return False


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("="*80)
    print("市场环境过滤器测试")
    print("="*80)
    print()

    # 加载数据
    try:
        df = pd.read_csv("btc_daily_ohlcv_2years.csv")
        df.columns = df.columns.str.strip()
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期').reset_index(drop=True)

        print(f"[OK] 数据加载成功: {len(df)} 天")
        print()

    except Exception as e:
        print(f"[ERROR] 数据加载失败: {e}")
        exit()

    # 创建过滤器
    filter = MarketFilter()

    # 测试1：不同时间点的市场环境
    print("【测试1】不同时间点的市场环境")
    print("-"*80)

    test_dates = [
        '2024-03-05',  # 牛市阶段（做空失败）
        '2024-10-01',  # 震荡阶段
        '2025-08-15',  # 熊市阶段（做空成功）
        '2025-10-10',  # 熊市阶段（完美案例）
    ]

    for date_str in test_dates:
        target_date = pd.to_datetime(date_str)
        df_before = df[df['日期'] < target_date]

        if len(df_before) >= 60:
            env = filter.check_market_environment(df_before, lookback=60)

            should_skip = filter.should_skip_short_alert(env)

            print(f"{date_str}:")
            print(f"  环境: {env['environment']}")
            print(f"  价格趋势: {env['price_trend']:+.2f}%")
            print(f"  成交量趋势: {env['vol_trend']:+.2f}%")
            print(f"  原因: {env['reason']}")
            print(f"  跳过做空: {'[YES] 是（牛市）' if should_skip else '[NO] 否（熊市/震荡）'}")
            print()

    # 测试2：遍历整个回测期，统计市场环境分布
    print("[测试2] 2年市场环境分布统计")
    print("-"*80)

    bull_count = 0
    bear_count = 0
    neutral_count = 0

    for idx in range(60, len(df)):
        df_before = df.iloc[:idx]
        env = filter.check_market_environment(df_before, lookback=60)

        if env['environment'] in ['BULL', 'STRONG_BULL']:
            bull_count += 1
        elif env['environment'] in ['BEAR', 'STRONG_BEAR']:
            bear_count += 1
        else:
            neutral_count += 1

    total = bull_count + bear_count + neutral_count

    print(f"牛市天数: {bull_count} 天 ({bull_count/total*100:.1f}%)")
    print(f"熊市天数: {bear_count} 天 ({bear_count/total*100:.1f}%)")
    print(f"震荡天数: {neutral_count} 天 ({neutral_count/total*100:.1f}%)")
    print()

    print("="*80)
    print("[OK] 市场环境过滤器测试完成")
    print("="*80)
