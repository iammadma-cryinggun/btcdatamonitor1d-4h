FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY btcv4_hybrid_telegram_bot.py .
COPY btc_v70_predator_engine_fixed.py .
COPY market_filter.py .
COPY btc_daily_ohlcv_2years.csv .

# 设置环境变量（在Zeabur中会被覆盖）
ENV TELEGRAM_TOKEN=""
ENV CHAT_ID=""
ENV COINALYZE_API_KEY=""

# 启动命令
CMD ["python", "btcv4_hybrid_telegram_bot.py"]
