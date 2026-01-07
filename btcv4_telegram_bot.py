# -*- coding: utf-8 -*-
"""
BTC V4.0 Telegram交互式Bot - 部署版
支持环境变量配置
"""
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import requests
from datetime import datetime, timedelta
import os
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 从环境变量读取配置
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
COINALYZE_API_KEY = os.getenv('COINALYZE_API_KEY')
COINALYZE_BASE_URL = "https://api.coinalyze.net/v1"

# 验证必需的环境变量
if not TELEGRAM_TOKEN:
    raise ValueError("缺少环境变量: TELEGRAM_TOKEN")
if not CHAT_ID:
    raise ValueError("缺少环境变量: CHAT_ID")
if not COINALYZE_API_KEY:
    raise ValueError("缺少环境变量: COINALYZE_API_KEY")

class BTCV4Bot:
    """BTC V4.0交互式Bot"""

    def __init__(self):
        # 加载历史数据
        self.df = pd.read_csv('btc_daily_ohlcv_2years.csv')
        self.df.columns = self.df.columns.str.strip()
        self.df['日期'] = pd.to_datetime(self.df['日期'])
        self.df = self.df.sort_values('日期').reset_index(drop=True)
        print(f"✅ 历史数据加载完成: {len(self.df)} 天")

        # 日志文件
        self.log_file = 'btcv4_query_log.csv'
        self._init_log_file()

    def _init_log_file(self):
        """初始化日志文件"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'query_type',
                    'price',
                    'volume',
                    'ls_ratio',
                    'oi_million',
                    'liquidation_usd',
                    'ls_rank_pct',
                    'oi_rank_pct',
                    'vol_rank_pct',
                    'liq_rank_pct',
                    'crash_score',
                    'surge_score',
                    'status_emoji',
                    'status_text',
                    'suggestion',
                    'actual_outcome',  # 手动填写：涨/跌/横盘
                    'notes'  # 手动填写备注
                ])
            print(f"✅ 日志文件已创建: {self.log_file}")
        else:
            print(f"✅ 日志文件已存在: {self.log_file}")

    def _log_query(self, query_type, diagnosis):
        """记录查询日志"""
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
                    getattr(self, 'last_status_emoji', ''),
                    getattr(self, 'last_status_text', ''),
                    getattr(self, 'last_suggestion', ''),
                    '',  # actual_outcome 留空给手动填写
                    ''   # notes 留空给手动填写
                ])
            print(f"📝 查询已记录到日志")
        except Exception as e:
            print(f"⚠️  日志记录失败: {e}")

    async def cmd_1d(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """日线诊断命令"""
        msg = await update.message.reply_text("⏳ 正在获取日线数据...")

        try:
            # 获取实时数据
            result = self.get_realtime_data()
            if not result:
                await msg.edit_text("❌ 无法获取实时数据")
                return

            # 计算诊断
            diagnosis = self.calculate_diagnosis(result)

            # 格式化报告
            report = self.format_diagnosis_report(diagnosis, "日线")

            await msg.edit_text(report, parse_mode='Markdown')

            # 记录日志
            self._log_query("1d", diagnosis)

        except Exception as e:
            await msg.edit_text(f"❌ 诊断失败: {str(e)}")

    async def cmd_1h(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """1小时分析命令"""
        # 解析参数
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

            # 使用历史最新LS、OI、Liq
            latest_ls = self.df['多空比(LS)'].dropna().tail(1).iloc[0]
            latest_oi = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]
            latest_liq = self.df['清算量(美元)'].dropna().tail(1).iloc[0]

            # 构建数据
            result = {
                'price': price,
                'volume': volume,
                'ls': latest_ls,
                'oi': latest_oi,
                'liq': latest_liq,
                'source': '1H手动输入'
            }

            # 计算诊断
            diagnosis = self.calculate_diagnosis(result)

            # 格式化报告
            report = self.format_diagnosis_report(diagnosis, "1小时")

            await update.message.reply_text(report, parse_mode='Markdown')

            # 记录日志
            self._log_query("1h", diagnosis)

        except ValueError:
            await update.message.reply_text("❌ 价格和成交量必须是数字")

    async def cmd_4h(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """4小时分析命令"""
        # 解析参数
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

            # 4H成交量需要乘以6来估算日成交量（粗略）
            estimated_daily_volume = volume * 6

            # 使用历史最新LS、OI、Liq
            latest_ls = self.df['多空比(LS)'].dropna().tail(1).iloc[0]
            latest_oi = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]
            latest_liq = self.df['清算量(美元)'].dropna().tail(1).iloc[0]

            # 构建数据
            result = {
                'price': price,
                'volume': estimated_daily_volume,
                'ls': latest_ls,
                'oi': latest_oi,
                'liq': latest_liq,
                'source': '4H手动输入'
            }

            # 计算诊断
            diagnosis = self.calculate_diagnosis(result)

            # 格式化报告
            report = self.format_diagnosis_report(diagnosis, "4小时")

            await update.message.reply_text(report, parse_mode='Markdown')

            # 记录日志
            self._log_query("4h", diagnosis)

        except ValueError:
            await update.message.reply_text("❌ 价格和成交量必须是数字")

    def get_realtime_data(self):
        """获取实时数据"""
        result = {}

        # Binance价格和成交量（获取昨天的已收盘日线数据）
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {'symbol': 'BTCUSDT', 'interval': '1d', 'limit': 2}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()[0]  # 取data[0]是昨天已收盘的日线，data[1]是今天正在形成中的

            result['price'] = float(data[4])
            result['volume'] = float(data[5])

        except Exception as e:
            print(f"Binance API错误: {e}")
            return None

        # Coinalyze LS-Ratio
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=2)
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
            print(f"LS API错误: {e}")
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
            print(f"OI API错误: {e}")
            result['oi'] = self.df['持仓量(OI-百万)'].dropna().tail(1).iloc[0]

        # 清算量（最新非零）
        liq_series = self.df['清算量(美元)'].dropna()
        liq_nonzero = liq_series[liq_series > 0]
        if len(liq_nonzero) > 0:
            result['liq'] = liq_nonzero.tail(1).iloc[0]
        else:
            result['liq'] = liq_series.tail(1).iloc[0]

        return result

    def calculate_diagnosis(self, data):
        """计算诊断结果"""
        # 获取参考窗口
        ref_window = self.df.tail(30).copy()

        # 计算百分位
        def get_percentile(value, series):
            clean_series = series.dropna()
            combined = pd.concat([clean_series, pd.Series([value])], ignore_index=True)
            return combined.rank(pct=True).iloc[-1] * 100

        ls_rank = get_percentile(data['ls'], ref_window['多空比(LS)'])
        oi_rank = get_percentile(data['oi'], ref_window['持仓量(OI-百万)'])
        vol_rank = get_percentile(data['volume'], ref_window['成交量(BTC)'])
        liq_rank = get_percentile(data['liq'], ref_window['清算量(美元)'])

        # 计算评分
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
            'source': data.get('source', '日线API')
        }

    def format_diagnosis_report(self, diagnosis, timeframe):
        """格式化诊断报告"""
        # 状态判定
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

        # 保存状态供日志使用
        self.last_status_emoji = status_emoji
        self.last_status_text = status_text
        self.last_suggestion = suggestion

        report = f"""
📊 *BTC V4.0 诊断报告* ({timeframe})

💰 价格: `${diagnosis['price']:,.2f}`
📊 成交量: `{diagnosis['volume']:,.0f}` BTC
📈 LS-Ratio: `{diagnosis['ls']:.3f}`
💼 OI: `{diagnosis['oi']:,.2f}` 百万
💥 清算量: `${diagnosis['liq']:,.0f}`

*📈 维度强度（30天分位数）*
• LS: `{diagnosis['ls_rank']:.1f}%` {'🔥极高' if diagnosis['ls_rank']>=90 else '⚠️偏高' if diagnosis['ls_rank']>=75 else '✅正常'}
• OI: `{diagnosis['oi_rank']:.1f}%`
• Vol: `{diagnosis['vol_rank']:.1f}%`
• Liq: `{diagnosis['liq_rank']:.1f}%`

*🎯 V4.0综合评分*
• 暴跌风险: `{diagnosis['crash_score']:.1f}` {'🔴危险' if diagnosis['crash_score']>=75 else '🟡警戒' if diagnosis['crash_score']>=60 else '✅安全'}
• 暴涨机会: `{diagnosis['surge_score']:.1f}` {'🔵机会' if diagnosis['surge_score']>=75 else '✅正常'}

*📋 状态判定*
{status_emoji} *{status_text}*（Crash: {diagnosis['crash_score']:.1f}, Surge: {diagnosis['surge_score']:.1f}）

💡 *建议*: {suggestion}

🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
📡 数据源: {diagnosis['source']}
        """
        return report


# ==================== [主程序] ====================
if __name__ == "__main__":
    print("="*100)
    print("BTC V4.0 Telegram Bot启动中...")
    print("="*100)

    # 创建Bot实例
    bot = BTCV4Bot()

    # 创建Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 注册命令处理器 - 只保留三个核心命令
    application.add_handler(CommandHandler("1d", bot.cmd_1d))
    application.add_handler(CommandHandler("1h", bot.cmd_1h))
    application.add_handler(CommandHandler("4h", bot.cmd_4h))

    print("✅ Bot已启动，可以接收命令了")
    print("="*100)
    print("\n可用命令:")
    print("  /1d - 查看日线诊断报告")
    print("  /1h [价格] [成交量] - 分析1H数据（示例: /1h 91716 1258.06）")
    print("  /4h [价格] [成交量] - 分析4H数据（示例: /4h 92000 15000）")
    print("="*100)

    # 运行Bot
    application.run_polling()
