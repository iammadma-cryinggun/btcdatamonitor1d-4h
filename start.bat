@echo off
chcp 65001 >nul
echo ==========================================
echo BTC V4.0 Telegram Bot 启动中...
echo ==========================================
echo.

REM 检查数据文件
if not exist "btc_daily_ohlcv_2years.csv" (
    echo ❌ 错误: 缺少历史数据文件 btc_daily_ohlcv_2years.csv
    pause
    exit /b 1
)

echo ✅ 数据文件检查通过
echo ✅ 启动Bot...
echo.

REM 启动Bot
python btcv4_telegram_bot.py

pause
