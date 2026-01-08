@echo off
chcp 65001 >nul
echo ==========================================
echo BTC V4.0 + V4.0.1 混合Bot 启动中...
echo ==========================================
echo.
echo 混合版本特性:
echo   - 同时运行V4.0和V4.0.1两个系统
echo   - 对比两个系统的预警准确性
echo   - 两个独立的日志文件
echo   - 统一的Telegram交互接口
echo.
echo ==========================================
echo.

REM 检查数据文件
if not exist "btc_daily_ohlcv_2years.csv" (
    echo [ERROR] 缺少历史数据文件 btc_daily_ohlcv_2years.csv
    pause
    exit /b 1
)

REM 检查依赖文件
if not exist "btc_v70_predator_engine_fixed.py" (
    echo [ERROR] 缺少 V7.0 引擎文件
    pause
    exit /b 1
)

if not exist "market_filter.py" (
    echo [ERROR] 缺少市场过滤器文件
    pause
    exit /b 1
)

echo [OK] 数据文件检查通过
echo [OK] V7.0 引擎文件检查通过
echo [OK] 市场过滤器检查通过
echo [OK] 启动混合Bot...
echo.

REM 启动混合Bot
python btcv4_hybrid_telegram_bot.py

pause
