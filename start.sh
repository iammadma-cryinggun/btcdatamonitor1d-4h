#!/bin/bash
# BTC V4.0 Telegram Bot 启动脚本

echo "=========================================="
echo "BTC V4.0 Telegram Bot 启动中..."
echo "=========================================="

# 检查环境变量
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ 错误: 缺少环境变量 TELEGRAM_TOKEN"
    exit 1
fi

if [ -z "$CHAT_ID" ]; then
    echo "❌ 错误: 缺少环境变量 CHAT_ID"
    exit 1
fi

if [ -z "$COINALYZE_API_KEY" ]; then
    echo "❌ 错误: 缺少环境变量 COINALYZE_API_KEY"
    exit 1
fi

# 检查数据文件
if [ ! -f "btc_daily_ohlcv_2years.csv" ]; then
    echo "❌ 错误: 缺少历史数据文件 btc_daily_ohlcv_2years.csv"
    exit 1
fi

echo "✅ 环境检查通过"
echo "✅ 启动Bot..."
echo ""

# 启动Bot
python btcv4_telegram_bot.py
