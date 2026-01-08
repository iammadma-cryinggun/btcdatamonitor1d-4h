# -*- coding: utf-8 -*-
"""
BTC V4.0 + V4.0.1 混合版 Telegram Bot

功能：
- 同时运行V4.0和V4.0.1两个系统
- 对比两个系统的预警准确性
- 独立记录两个系统的日志
- 统一的Telegram交互接口
"""
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import os
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 导入V4.0.1的V7.0引擎和市场过滤器
from btc_v70_predator_engine_fixed import V70PredatorEngineFixed
from market_filter import MarketFilter

# 从环境变量读取配置（自动去除前后空格）
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()
CHAT_ID = os.getenv('CHAT_ID', '').strip()
COINALYZE_API_KEY = os.getenv('COINALYZE_API_KEY', '').strip()
COINALYZE_BASE_URL = "https://api.coinalyze.net/v1"

# 验证必需的环境变量
if not TELEGRAM_TOKEN:
    raise ValueError("缺少环境变量: TELEGRAM_TOKEN")
if not CHAT_ID:
    raise ValueError("缺少环境变量: CHAT_ID")
if not COINALYZE_API_KEY:
    raise ValueError("缺少环境变量: COINALYZE_API_KEY")

class BTCV40System:
    """V4.0系统 - 百分位评分"""

    def __init__(self, df):
        self.df = df
        self.log_file = 'btcv4_query_log.csv'
        self.last_status_emoji = ''
        self.last_status_text = ''
        self.last_suggestion = ''
        self._init_log_file()

    def _init_log_file(self):
        """初始化V4.0日志文件"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'query_type', 'price', 'volume', 'ls_ratio',
                    'oi_million', 'liquidation_usd', 'ls_rank_pct', 'oi_rank_pct',
                    'vol_rank_pct', 'liq_rank_pct', 'crash_score', 'surge_score',
                    'status_emoji', 'status_text', 'suggestion',
                    'actual_outcome', 'notes'
                ])
            print(f"[V4.0] 日志文件已创建: {self.log_file}")

    def calculate_diagnosis(self, data):
        """计算V4.0诊断结果"""
        ref_window = self.df.tail(30).copy()

        def get_percentile(value, series):
            clean_series = series.dropna()
            combined = pd.concat([clean_series, pd.Series([value])], ignore_index=True)
            return combined.rank(pct=True).iloc[-1] * 100

        ls_rank = get_percentile(data['ls'], ref_window['多空比(LS)'])
        oi_rank = get_percentile(data['oi'], ref_window['持仓量(OI-百万)'])
        vol_rank = get_percentile(data['volume'], ref_window['成交量(BTC)'])
        liq_rank = get_percentile(data['liq'], ref_window['清算量(美元)'])

        crash_score = (ls_rank * 0.50 + vol_rank * 0.25 + liq_rank * 0.15 + oi_rank * 0.10)
        surge_score = ((100 - ls_rank) * 0.50 + oi_rank * 0.25 + vol_rank * 0.15 + liq_rank * 0.10)

        return {
            'price': data['price'],
            'ls': data['ls'],
            'oi': data['oi'],
            'volume': data['volume'],
            'liq': data['liq'],
            'ls_rank': ls_rank,
            'oi_rank': oi_rank,
            'vol_rank': vol_rank,
            'liq_rank': liq_rank,
            'crash_score': crash_score,
            'surge_score': surge_score,
            'source': data.get('source', 'API')
        }

    def format_report(self, diagnosis, timeframe):
        """格式化V4.0报告"""
        if diagnosis['crash_score'] >= 85:
            status_emoji = "🔴"
            status_text = "极高风险区"
            suggestion = "在图表上寻找做空机会"
        elif diagnosis['crash_score'] >= 75:
            status_emoji = "🟠"
            status_text = "高风险区"
            suggestion = "谨慎做多，可考虑做空"
        elif diagnosis['surge_score'] >= 75:
            status_emoji = "🟢"
            status_text = "机会区"
            suggestion = "在图表上寻找做多机会"
        elif diagnosis['crash_score'] >= 60 or diagnosis['surge_score'] >= 60:
            status_emoji = "🟡"
            status_text = "警戒区"
            suggestion = "观察为主，小仓位试探"
        else:
            status_emoji = "✅"
            status_text = "安全区"
            suggestion = "等待明确信号"

        self.last_status_emoji = status_emoji
        self.last_status_text = status_text
        self.last_suggestion = suggestion

        # 转义alert level中的星号
        report = f"""
*📊 V4.0 系统* \\({timeframe}\\)
{status_emoji} \\*{status_text}\\*
💰 价格: `${diagnosis['price']:,.2f}`
📊 LS: `{diagnosis['ls']:.3f}` \\(30天分位: `{diagnosis['ls_rank']:.1f}%`\\)
💼 OI: `${diagnosis['oi']:,.2f}M`
💥 清算: `${diagnosis['liq']:,.0f}`

*📈 V4.0评分*
• 暴跌风险: `{diagnosis['crash_score']:.1f}` {'🔴危险' if diagnosis['crash_score']>=75 else '🟡警戒' if diagnosis['crash_score']>=60 else '✅安全'}
• 暴涨机会: `{diagnosis['surge_score']:.1f}` {'🔵机会' if diagnosis['surge_score']>=75 else '✅正常'}

💡 *建议*: {suggestion}
"""
        return report

    def log_query(self, query_type, diagnosis):
        """记录V4.0查询日志"""
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    query_type,
                    diagnosis['price'],
                    diagnosis['volume'],
                    diagnosis['ls'],
                    diagnosis['oi'],
                    diagnosis['liq'],
                    f"{diagnosis['ls_rank']:.1f}",
                    f"{diagnosis['oi_rank']:.1f}",
                    f"{diagnosis['vol_rank']:.1f}",
                    f"{diagnosis['liq_rank']:.1f}",
                    f"{diagnosis['crash_score']:.1f}",
                    f"{diagnosis['surge_score']:.1f}",
                    self.last_status_emoji,
                    self.last_status_text,
                    self.last_suggestion,
                    '',  # actual_outcome
                    ''   # notes
                ])
        except Exception as e:
            print(f"[V4.0] 日志记录失败: {e}")


class BTCV41System:
    """V4.0.1系统 - V7.0引擎 + 市场过滤器"""

    def __init__(self, df):
        self.df = df

        # 计算ATR
        atr_period = 14
        high = df["最高价"]
        low = df["最低价"]
        close = df["收盘价"]
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.df['ATR'] = true_range.ewm(span=atr_period, adjust=False).mean()

        # 初始化V7.0引擎
        self.engine = V70PredatorEngineFixed(
            zscore_window=30,
            delta_ls_window=1,
            delta_ls_accel_window=1,
            ema_span=5,
            data_frequency_hours=24
        )

        # 初始化市场过滤器
        self.market_filter = MarketFilter()

        # 预热引擎
        for idx, row in self.df.iterrows():
            self.engine.update_data(row)

        # 日志文件
        self.log_file = 'btcv4_1_alert_log.csv'
        self._init_log_file()

    def _init_log_file(self):
        """初始化V4.0.1日志文件"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'alert_level', 'pulse_score', 'direction',
                    'market_environment', 'filter_action', 'price', 'ls_ratio',
                    'delta2_ls', 'z_liq', 'z_vol', 'z_div_oi',
                    'actual_outcome', 'notes'
                ])
            print(f"[V4.0.1] 日志文件已创建: {self.log_file}")

    def get_alert(self, realtime_data):
        """获取V4.0.1预警"""
        # 构造数据格式
        row = {
            '日期': datetime.now(),
            '开盘价': realtime_data['price'],
            '最高价': realtime_data['price'] * 1.005,
            '最低价': realtime_data['price'] * 0.995,
            '收盘价': realtime_data['price'],
            '成交量(BTC)': realtime_data['volume'],
            '多空比(LS)': realtime_data['ls'],
            '持仓量(OI-百万)': realtime_data['oi'],
            '清算量(美元)': realtime_data['liq'],
            '资金费率(%)': realtime_data.get('fr', 0),
            'ATR': self.df['ATR'].iloc[-1]
        }

        # 更新引擎
        self.engine.update_data(row)

        # 获取预警
        alert = self.engine.get_predator_alert()

        # 获取市场环境
        market_env = self.market_filter.check_market_environment(self.df, lookback=60)

        # 判断是否过滤
        filter_action = 'EXECUTED'
        if alert['direction'] == 'SHORT':
            should_skip = self.market_filter.should_skip_short_alert(market_env)
            if should_skip:
                filter_action = 'FILTERED'

        return alert, market_env, filter_action

    def format_report(self, realtime_data, alert, market_env, filter_action):
        """格式化V4.0.1报告"""
        env_emoji = {
            'STRONG_BULL': '🚀 强牛市',
            'BULL': '📈 牛市',
            'NEUTRAL': '⏸️ 震荡',
            'BEAR': '📉 熊市',
            'STRONG_BEAR': '🔻 强熊市'
        }
        env_text = env_emoji.get(market_env['environment'], market_env['environment'])

        if filter_action == 'FILTERED':
            filter_status = f"🔕 \\*\\*已过滤\\*\\* ({env_text})"
            filter_reason = f"牛市阶段跳过做空（价格趋势: {market_env['price_trend']:+.1f}%）"
        else:
            filter_status = f"✅ \\*\\*执行\\*\\* ({env_text})"
            filter_reason = f"市场环境适合（价格趋势: {market_env['price_trend']:+.1f}%）"

        level_emoji = {
            'LEVEL 3 (坍塌)': '🔴',
            'LEVEL 2 (临界)': '🟠',
            'LEVEL 1 (监视)': '🟡',
            'NO_SIGNAL': '✅'
        }
        level_emoji_text = level_emoji.get(alert['level'], '⚪')

        # 转义alert level中的特殊字符
        safe_level = alert['level'].replace('(', '\\(').replace(')', '\\)').replace('*', '\\*')

        details = alert['details']

        report = f"""
*🔍 V4.0.1 系统* \\(V7.0引擎\\)
{level_emoji_text} \\*\\*{safe_level}\\*\\* \\(Score: {alert['pulse_score']:.1f}\\)
• 方向: `{alert['direction']}`
• Z\\_Liq: `{details.get('z_liq', 0):.2f}`
• Δ²LS: `{details.get('delta2_ls', 0):.4f}`

*🌍 市场环境*
{filter_status}
{filter_reason}

💰 价格: `${realtime_data['price']:,.2f}`
📊 LS: `{realtime_data['ls']:.3f}`
💼 OI: `${realtime_data['oi']:,.2f}M`
"""
        if 'LEVEL 3' in alert['level']:
            if filter_action == 'FILTERED':
                report += "⚠️ LEVEL 3但牛市，建议跳过\n"
            else:
                report += "🚨 LEVEL 3且适合，\\*\\*坚决做空\\*\\*\n"
        elif 'LEVEL 2' in alert['level']:
            report += "⚠️ LEVEL 2临界状态\n"
        else:
            report += "✅ 无明确预警\n"

        return report

    def log_alert(self, alert, market_env, filter_action):
        """记录V4.0.1预警日志"""
        try:
            details = alert['details']
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    alert['level'],
                    f"{alert['pulse_score']:.2f}",
                    alert['direction'],
                    market_env['environment'],
                    filter_action,
                    details['current_price'],
                    details.get('ls_ratio', 0),
                    details.get('delta2_ls', 0),
                    details.get('z_liq', 0),
                    details.get('z_vol', 0),
                    details.get('z_div_oi', 0),
                    '',  # actual_outcome
                    ''   # notes
                ])
        except Exception as e:
            print(f"[V4.0.1] 日志记录失败: {e}")


class BTCHybridBot:
    """BTC V4.0 + V4.0.1 混合Bot"""

    def __init__(self):
        # 加载历史数据
        self.df = pd.read_csv('btc_daily_ohlcv_2years.csv')
        self.df.columns = self.df.columns.str.strip()
        self.df['日期'] = pd.to_datetime(self.df['日期'])
        self.df = self.df.sort_values('日期').reset_index(drop=True)
        print(f"[OK] 历史数据加载完成: {len(self.df)} 天")

        # 初始化两个系统
        self.v40_system = BTCV40System(self.df)
        print(f"[OK] V4.0系统初始化完成")

        self.v41_system = BTCV41System(self.df)
        print(f"[OK] V4.0.1系统初始化完成")

        # 保存application引用
        self.application = None
        self.chat_id = CHAT_ID

    async def daily_monitoring_job(self, context: ContextTypes.DEFAULT_TYPE):
        """每日定时监控任务 - 同时运行两个系统"""
        try:
            print(f"\n{'='*100}")
            print(f"[定时任务] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 执行每日混合监控")
            print(f"{'='*100}")

            # 获取实时数据
            result = self.get_realtime_data()
            if not result:
                print("[ERROR] 定时监控失败：无法获取实时数据")
                return

            # V4.0诊断
            v40_diagnosis = self.v40_system.calculate_diagnosis(result)

            # V4.0.1预警
            v41_alert, market_env, filter_action = self.v41_system.get_alert(result)

            # 生成混合报告
            report = self.format_hybrid_report(result, v40_diagnosis, v41_alert, market_env, filter_action)

            # 发送到Telegram
            await context.bot.send_message(
                chat_id=self.chat_id,
                text=report,
                parse_mode='Markdown'
            )

            # 记录日志
            self.v40_system.log_query("daily_auto", v40_diagnosis)

            if 'LEVEL 3' in v41_alert['level'] and filter_action == 'EXECUTED':
                self.v41_system.log_alert(v41_alert, market_env, filter_action)

            print(f"[OK] 混合监控报告推送成功")

        except Exception as e:
            print(f"[ERROR] 定时监控失败: {str(e)}")
            import traceback
            traceback.print_exc()

    async def cmd_1d(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """V4.0: 日线诊断命令"""
        msg = await update.message.reply_text("⏳ 正在获取V4.0日线数据...")

        try:
            result = self.get_realtime_data()
            if not result:
                await msg.edit_text("❌ 无法获取实时数据")
                return

            diagnosis = self.v40_system.calculate_diagnosis(result)
            report = self.v40_system.format_report(diagnosis, "日线")

            await msg.edit_text(report, parse_mode='Markdown')
            self.v40_system.log_query("1d", diagnosis)

        except Exception as e:
            await msg.edit_text(f"❌ V4.0诊断失败: {str(e)}")

    async def cmd_1h(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """V4.0: 1小时分析命令"""
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ 参数错误\n\n格式: /1h [价格] [成交量]\n示例: /1h 91716 1258.06",
                parse_mode='Markdown'
            )
            return

        try:
            price = float(args[0])
            volume = float(args[1])

            latest_ls = self.df['多空比(LS)'].dropna().tail(1).iloc[0]
            latest_oi = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]
            latest_liq = self.df['清算量(美元)'].dropna().tail(1).iloc[0]

            result = {
                'price': price,
                'volume': volume,
                'ls': latest_ls,
                'oi': latest_oi,
                'liq': latest_liq,
                'source': '1H手动输入'
            }

            diagnosis = self.v40_system.calculate_diagnosis(result)
            report = self.v40_system.format_report(diagnosis, "1小时")

            await update.message.reply_text(report, parse_mode='Markdown')
            self.v40_system.log_query("1h", diagnosis)

        except ValueError:
            await update.message.reply_text("❌ 价格和成交量必须是数字")

    async def cmd_4h(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """V4.0: 4小时分析命令"""
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ 参数错误\n\n格式: /4h [价格] [成交量]\n示例: /4h 92000 15000",
                parse_mode='Markdown'
            )
            return

        try:
            price = float(args[0])
            volume = float(args[1])

            estimated_daily_volume = volume * 6

            latest_ls = self.df['多空比(LS)'].dropna().tail(1).iloc[0]
            latest_oi = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]
            latest_liq = self.df['清算量(美元)'].dropna().tail(1).iloc[0]

            result = {
                'price': price,
                'volume': estimated_daily_volume,
                'ls': latest_ls,
                'oi': latest_oi,
                'liq': latest_liq,
                'source': '4H手动输入'
            }

            diagnosis = self.v40_system.calculate_diagnosis(result)
            report = self.v40_system.format_report(diagnosis, "4小时")

            await update.message.reply_text(report, parse_mode='Markdown')
            self.v40_system.log_query("4h", diagnosis)

        except ValueError:
            await update.message.reply_text("❌ 价格和成交量必须是数字")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """V4.0.1: 查看当前状态命令"""
        msg = await update.message.reply_text("⏳ 正在获取混合状态...")

        try:
            result = self.get_realtime_data()
            if not result:
                await msg.edit_text("❌ 无法获取实时数据")
                return

            # V4.0诊断
            v40_diagnosis = self.v40_system.calculate_diagnosis(result)

            # V4.0.1预警
            v41_alert, market_env, filter_action = self.v41_system.get_alert(result)

            # 生成混合报告
            report = self.format_hybrid_report(result, v40_diagnosis, v41_alert, market_env, filter_action)

            await msg.edit_text(report, parse_mode='Markdown')

            # 记录日志
            self.v40_system.log_query("status", v40_diagnosis)

            if 'LEVEL 3' in v41_alert['level'] and filter_action == 'EXECUTED':
                self.v41_system.log_alert(v41_alert, market_env, filter_action)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await msg.edit_text(f"❌ 状态查询失败: {str(e)}")

    async def cmd_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看当前实时市场数据"""
        msg = await update.message.reply_text("⏳ 正在获取实时数据...")

        try:
            result = self.get_current_data()
            if not result:
                await msg.edit_text("❌ 无法获取实时数据")
                return

            # 格式化实时数据报告
            change_emoji = "📈" if result['change_24h'] >= 0 else "📉"
            change_color = "+" if result['change_24h'] >= 0 else ""

            report = f"""
🔴 \\*\\*BTC实时市场数据\\*\\*

📡 \\*\\*数据来源\\*\\*: `{result['data_source']}`
🕐 \\*\\*更新时间\\*\\*: `{result['date'].strftime('%Y-%m-%d %H:%M:%S')}`

💰 \\*\\*当前价格\\*\\*: `${result['price']:,.2f}`
{change_emoji} \\*\\*24h变化\\*\\*: `{change_color}{result['change_24h']:.2f}%`
📊 \\*\\*24h最高\\*\\*: `${result['high_24h']:,.2f}`
📊 \\*\\*24h最低\\*\\*: `${result['low_24h']:,.2f}`
📦 \\*\\*24h成交量\\*\\*: `{result['volume']:,.0f} BTC`

━━━━━━━━━━━━━━━━━━━━
📊 \\*\\*多空比\\*\\*: `{result['ls']:.3f}`
💼 \\*\\*持仓量\\*\\*: `${result['oi']:,.2f}M`
💥 \\*\\*清算量\\*\\*: `${result['liq']:,.0f}`
📈 \\*\\*资金费率\\*\\*: `{result.get('fr', 0):.3f}%`

💡 这是目前最新的实时市场数据
            """

            await msg.edit_text(report, parse_mode='Markdown')

        except Exception as e:
            import traceback
            traceback.print_exc()
            await msg.edit_text(f"❌ 实时数据查询失败: {str(e)}")

    async def cmd_compare(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """对比两个系统的统计信息"""
        try:
            # V4.0统计
            if os.path.exists(self.v40_system.log_file):
                v40_df = pd.read_csv(self.v40_system.log_file)
                v40_total = len(v40_df)
                v40_high_risk = len(v40_df[v40_df['crash_score'] >= 75])
            else:
                v40_total = 0
                v40_high_risk = 0

            # V4.0.1统计
            if os.path.exists(self.v41_system.log_file):
                v41_df = pd.read_csv(self.v41_system.log_file)
                v41_total = len(v41_df)
                v41_level3 = len(v41_df[v41_df['alert_level'].str.contains('LEVEL 3', na=False)])
                v41_executed = len(v41_df[v41_df['filter_action'] == 'EXECUTED'])
                v41_filtered = len(v41_df[v41_df['filter_action'] == 'FILTERED'])
            else:
                v41_total = 0
                v41_level3 = 0
                v41_executed = 0
                v41_filtered = 0

            compare_report = f"""
📊 \\*V4.0 vs V4.0.1 对比统计\\*

*📈 V4.0 系统\\(百分位评分\\)*
• 总查询数: `{v40_total}` 次
• 高风险警报: `{v40_high_risk}` 次 \\(Crash >= 75\\)
• 准确率: 需要手动验证日志

*🔍 V4.0.1 系统\\(V7.0引擎\\)*
• 总预警数: `{v41_total}` 次
• LEVEL 3: `{v41_level3}` 次
• 已执行: `{v41_executed}` 次
• 已过滤: `{v41_filtered}` 次
• 回测准确率: 7天 `85.7%` | 30天 `100.0%`

*📝 日志文件*
• V4.0: `btcv4_query_log.csv`
• V4.0.1: `btcv4_1_alert_log.csv`

💡 \\*建议\\*: 定期下载日志文件，手动填写actual\\_outcome进行准确性对比

🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
            """
            await update.message.reply_text(compare_report, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ 对比查询失败: {str(e)}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助命令"""
        help_text = """
📖 \\*BTC混合Bot 使用说明\\*

*🔍 V4.0 命令\\(百分位评分\\)*
• /1d - 查看V4.0日线诊断
• /1h \\[价格\\] \\[成交量\\] - V4.0分析1H数据
• /4h \\[价格\\] \\[成交量\\] - V4.0分析4H数据

*🔍 V4.0.1 命令\\(V7.0引擎\\)*
• /status - 查看混合系统状态（已收盘交易日数据）
• /check - 查看实时市场数据（当前最新ticker）
• /compare - 对比两个系统的统计信息

*📊 系统特性*
• V4.0: 百分位评分 + Crash/Surge评分
• V4.0.1: V7.0引擎 + 三级预警 + 市场过滤器

*📅 数据说明*
• /status 使用已收盘交易日的完整数据（4.0和4.0.1时间同步）
• /check 使用当前最新的实时ticker数据

*📝 日志系统*
• 两个系统独立记录日志
• 定期下载日志文件手动验证准确性
• 对比两个系统的实际表现

*⏰ 定时任务*
• 每天UTC 0:00自动运行两个系统并发送混合报告
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    def get_realtime_data(self):
        """获取实时数据（最后一个已收盘的交易日）"""
        result = {}

        # Binance价格和成交量
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {'symbol': 'BTCUSDT', 'interval': '1d', 'limit': 5}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            all_klines = response.json()

            import time
            current_time = int(time.time() * 1000)

            selected_kline = None
            for kline in reversed(all_klines):
                close_time = int(kline[6])
                if close_time < current_time:
                    selected_kline = kline
                    break

            if selected_kline is None:
                selected_kline = all_klines[-2]

            result['price'] = float(selected_kline[4])
            result['volume'] = float(selected_kline[5])
            # 添加K线日期（转换为北京时间）
            close_time_ts = int(selected_kline[6]) / 1000
            result['date'] = datetime.fromtimestamp(close_time_ts)
            result['data_source'] = 'API (已收盘交易日)'

        except Exception as e:
            print(f"[ERROR] Binance API错误: {e}")
            return None

        # Coinalyze LS-Ratio
        try:
            now = datetime.now()
            to_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            from_date = to_date - timedelta(days=3)
            from_ts = int(from_date.timestamp())
            to_ts = int(to_date.timestamp())

            url = f"{COINALYZE_BASE_URL}/long-short-ratio-history"
            params = {
                'symbols': 'BTCUSD_PERP.A',
                'interval': 'daily',
                'from': from_ts,
                'to': to_ts
            }
            headers = {'Authorization': f'Bearer {COINALYZE_API_KEY}'}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()[0]['history']
                for item in reversed(data):
                    if item.get('r') is not None:
                        result['ls'] = item['r']
                        break
            else:
                result['ls'] = self.df['多空比(LS)'].dropna().tail(1).iloc[0]

        except Exception as e:
            print(f"[ERROR] LS API错误: {e}")
            result['ls'] = self.df['多空比(LS)'].dropna().tail(1).iloc[0]

        # Coinalyze OI
        try:
            url = f"{COINALYZE_BASE_URL}/open-interest-history"
            params = {
                'symbols': 'BTCUSD_PERP.A',
                'interval': 'daily',
                'from': from_ts,
                'to': to_ts
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()[0]['history']
                for item in reversed(data):
                    if item.get('c') is not None:
                        result['oi'] = item['c'] / 1_000_000
                        break
            else:
                result['oi'] = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]

        except Exception as e:
            print(f"[ERROR] OI API错误: {e}")
            result['oi'] = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]

        # 清算量
        liq_series = self.df['清算量(美元)'].dropna()
        liq_nonzero = liq_series[liq_series > 0]
        if len(liq_nonzero) > 0:
            result['liq'] = liq_nonzero.tail(1).iloc[0]
        else:
            result['liq'] = liq_series.tail(1).iloc[0]

        # 资金费率
        try:
            url = f"{COINALYZE_BASE_URL}/funding-rate-history"
            params = {
                'symbols': 'BTCUSD_PERP.A',
                'interval': 'daily',
                'from': from_ts,
                'to': to_ts
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()[0]['history']
                for item in reversed(data):
                    if item.get('r') is not None:
                        result['fr'] = item['r']
                        break
            else:
                result['fr'] = self.df['资金费率(%)'].dropna().tail(1).iloc[0]

        except Exception as e:
            result['fr'] = self.df['资金费率(%)'].dropna().tail(1).iloc[0]

        return result

    def get_current_data(self):
        """获取当前最新ticker数据（实时）"""
        result = {}

        try:
            # 获取当前ticker价格
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': 'BTCUSDT'}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            ticker = response.json()

            result['price'] = float(ticker['lastPrice'])
            result['volume'] = float(ticker['volume'])
            result['change_24h'] = float(ticker['priceChangePercent'])
            result['high_24h'] = float(ticker['highPrice'])
            result['low_24h'] = float(ticker['lowPrice'])
            result['date'] = datetime.now()
            result['data_source'] = 'API (实时ticker)'

            # 获取当前LS/OI/FR（使用最新的API数据）
            now = datetime.now()
            to_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            from_date = to_date - timedelta(days=3)
            from_ts = int(from_date.timestamp())
            to_ts = int(to_date.timestamp())

            headers = {'Authorization': f'Bearer {COINALYZE_API_KEY}'}

            # LS-Ratio
            try:
                url = f"{COINALYZE_BASE_URL}/long-short-ratio-history"
                params = {
                    'symbols': 'BTCUSD_PERP.A',
                    'interval': 'daily',
                    'from': from_ts,
                    'to': to_ts
                }
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()[0]['history']
                    for item in reversed(data):
                        if item.get('r') is not None:
                            result['ls'] = item['r']
                            break
                else:
                    result['ls'] = self.df['多空比(LS)'].dropna().tail(1).iloc[0]
            except:
                result['ls'] = self.df['多空比(LS)'].dropna().tail(1).iloc[0]

            # OI
            try:
                url = f"{COINALYZE_BASE_URL}/open-interest-history"
                params = {
                    'symbols': 'BTCUSD_PERP.A',
                    'interval': 'daily',
                    'from': from_ts,
                    'to': to_ts
                }
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()[0]['history']
                    for item in reversed(data):
                        if item.get('c') is not None:
                            result['oi'] = item['c'] / 1_000_000
                            break
                else:
                    result['oi'] = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]
            except:
                result['oi'] = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]

            # FR
            try:
                url = f"{COINALYZE_BASE_URL}/funding-rate-history"
                params = {
                    'symbols': 'BTCUSD_PERP.A',
                    'interval': 'daily',
                    'from': from_ts,
                    'to': to_ts
                }
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()[0]['history']
                    for item in reversed(data):
                        if item.get('r') is not None:
                            result['fr'] = item['r']
                            break
                else:
                    result['fr'] = self.df['资金费率(%)'].dropna().tail(1).iloc[0]
            except:
                result['fr'] = self.df['资金费率(%)'].dropna().tail(1).iloc[0]

            # 清算量（使用历史数据最新值）
            liq_series = self.df['清算量(美元)'].dropna()
            liq_nonzero = liq_series[liq_series > 0]
            if len(liq_nonzero) > 0:
                result['liq'] = liq_nonzero.tail(1).iloc[0]
            else:
                result['liq'] = liq_series.tail(1).iloc[0]

        except Exception as e:
            print(f"[ERROR] 获取实时ticker失败: {e}")
            return None

        return result

    def format_hybrid_report(self, data, v40_diagnosis, v41_alert, market_env, filter_action):
        """格式化混合报告"""
        # 获取数据日期（如果有的话）
        data_date = data.get('date', datetime.now())
        data_source = data.get('data_source', 'CSV (历史数据)')

        report = f"""
📊 \\*BTC混合系统监控报告\\*

📅 \\*\\*数据日期\\*\\*: `{data_date.strftime('%Y-%m-%d')}`
📡 \\*\\*数据来源\\*\\*: `{data_source}`

💰 价格: `${data['price']:,.2f}`
📊 LS: `{data['ls']:.3f}`
💼 OI: `${data['oi']:,.2f}M`
💥 清算: `${data['liq']:,.0f}`
📈 FR: `{data.get('fr', 0):.3f}%`

{self.v40_system.format_report(v40_diagnosis, "实时")}

{self.v41_system.format_report(data, v41_alert, market_env, filter_action)}

🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
📈 两个系统独立记录日志，便于对比准确性
        """
        return report


# ==================== [主程序] ====================
if __name__ == "__main__":
    print("="*100)
    print("BTC V4.0 + V4.0.1 混合Bot启动中...")
    print("="*100)

    # 创建Bot实例
    bot = BTCHybridBot()

    # 创建Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 保存application引用
    bot.application = application

    # 注册V4.0命令处理器
    application.add_handler(CommandHandler("1d", bot.cmd_1d))
    application.add_handler(CommandHandler("1h", bot.cmd_1h))
    application.add_handler(CommandHandler("4h", bot.cmd_4h))

    # 注册V4.0.1命令处理器
    application.add_handler(CommandHandler("status", bot.cmd_status))
    application.add_handler(CommandHandler("check", bot.cmd_check))
    application.add_handler(CommandHandler("compare", bot.cmd_compare))

    # 注册帮助命令
    application.add_handler(CommandHandler("help", bot.cmd_help))

    # 定时任务
    job_queue = application.job_queue

    # 每天UTC 0:00执行混合监控
    job_queue.run_daily(
        callback=bot.daily_monitoring_job,
        time=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
        name='daily_hybrid_monitoring'
    )

    print("[OK] 混合Bot已启动，可以接收命令了")
    print("[OK] 定时任务：每天UTC 0:00自动运行两个系统")
    print("="*100)
    print("\nV4.0命令:")
    print("  /1d - 查看V4.0日线诊断")
    print("  /1h [价格] [成交量] - V4.0分析1H数据")
    print("  /4h [价格] [成交量] - V4.0分析4H数据")
    print("\nV4.0.1命令:")
    print("  /status - 查看V4.0.1当前状态")
    print("  /compare - 对比两个系统的统计信息")
    print("\n通用:")
    print("  /help - 显示帮助信息")
    print("\n定时推送：每天UTC 0:00自动运行两个系统并发送混合报告")
    print("="*100)

    # 运行Bot
    application.run_polling()
