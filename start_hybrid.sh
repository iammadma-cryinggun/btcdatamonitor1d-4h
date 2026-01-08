#!/bin/bash
# BTC V4.0 + V4.0.1 混合Bot 启动脚本

echo "=========================================="
echo "BTC V4.0 + V4.0.1 混合Bot 启动中..."
echo "=========================================="
echo ""
echo "混合版本特性:"
echo "  - 同时运行V4.0和V4.0.1两个系统"
echo "  - 对比两个系统的预警准确性"
echo "  - 两个独立的日志文件"
echo "  - 统一的Telegram交互接口"
echo ""
echo "=========================================="
echo ""

# 检查环境变量
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "[ERROR] 缺少环境变量 TELEGRAM_TOKEN"
    exit 1
fi

if [ -z "$CHAT_ID" ]; then
    echo "[ERROR] 缺少环境变量 CHAT_ID"
    exit 1
fi

if [ -z "$COINALYZE_API_KEY" ]; then
    echo "[ERROR] 缺少环境变量 COINALYZE_API_KEY"
    exit 1
fi

# 检查数据文件
if [ ! -f "btc_daily_ohlcv_2years.csv" ]; then
    echo "[ERROR] 缺少历史数据文件 btc_daily_ohlcv_2years.csv"
    exit 1
fi

# 检查依赖文件
if [ ! -f "btc_v70_predator_engine_fixed.py" ]; then
    echo "[ERROR] 缺少 V7.0 引擎文件"
    exit 1
fi

if [ ! -f "market_filter.py" ]; then
    echo "[ERROR] 缺少市场过滤器文件"
    exit 1
fi

echo "[OK] 环境变量检查通过"
echo "[OK] 数据文件检查通过"
echo "[OK] V7.0 引擎文件检查通过"
echo "[OK] 市场过滤器检查通过"
echo "[OK] 启动混合Bot..."
echo ""

# 启动混合Bot
python btcv4_hybrid_telegram_bot.py
