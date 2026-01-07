# BTC V4.0 Telegram Bot - Zeabur部署指南

## 📋 功能说明

BTC V4.0 日线状态监控Bot，支持三个核心命令：
- `/1d` - 查看日线诊断报告（自动获取实时数据）
- `/1h [价格] [成交量]` - 分析1小时数据
- `/4h [价格] [成交量]` - 分析4小时数据

## 📦 文件清单

```
部署/
├── btcv4_telegram_bot.py      # 主程序
├── requirements.txt            # Python依赖
├── .env.example               # 环境变量示例
├── btc_daily_ohlcv_2years.csv # 历史数据（需要上传）
└── README.md                  # 本文档
```

## 🚀 Zeabur部署步骤

### 1. 准备历史数据文件

从本地复制 `btc_daily_ohlcv_2years.csv` 到部署文件夹：

```bash
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\btc_daily_ohlcv_2years.csv" "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\btc_daily_ohlcv_2years.csv"
```

### 2. 创建Zeabur项目

1. 访问 https://zeabur.com
2. 登录账号
3. 创建新项目

### 3. 部署服务

#### 方式A：通过Git部署（推荐）

1. 将部署文件夹推送到GitHub
2. 在Zeabur中选择"Deploy from GitHub"
3. 选择你的仓库
4. Zeabur会自动检测Python项目并部署

#### 方式B：通过Zeabur CLI部署

```bash
# 安装Zeabur CLI
npm install -g zeabur

# 登录
zeabur auth login

# 部署
cd "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署"
zeabur deploy
```

### 4. 配置环境变量

在Zeabur控制台中添加以下环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `TELEGRAM_TOKEN` | `8189663571:AAEvIUEBTfF_MfyKc7rWq5gQvgi4gAxZJrA` | Telegram Bot Token |
| `CHAT_ID` | `838429342` | 你的Telegram Chat ID |
| `COINALYZE_API_KEY` | `cd4bfa05-9951-4916-b02a-e4f45f992bc0` | Coinalyze API密钥 |

**重要**: 不要在代码中硬编码这些密钥！

### 5. 启动服务

Zeabur会自动检测 `requirements.txt` 并安装依赖，然后运行 `btcv4_telegram_bot.py`。

如果需要自定义启动命令，可以在Zeabur中设置：
```
启动命令: python btcv4_telegram_bot.py
```

### 6. 验证部署

部署完成后，在Telegram中发送命令测试：
```
/1d
```

如果收到诊断报告，说明部署成功！

## 📝 日志文件

Bot会自动记录所有查询到 `btcv4_query_log.csv`，包括：
- 查询时间
- 价格、成交量、LS、OI、清算量等数据
- 30天分位数
- Crash/Surge评分
- 状态判定

**定期下载日志文件进行准确性验证**：
1. 在Zeabur控制台找到日志文件
2. 下载到本地
3. 使用Excel或Python分析

## 🔧 常见问题

### Bot无法启动

检查：
1. 所有环境变量是否正确配置
2. `btc_daily_ohlcv_2years.csv` 是否已上传
3. Python依赖是否正确安装

### 收不到Telegram消息

检查：
1. TELEGRAM_TOKEN是否正确
2. Bot是否已启动（可以向Bot发送 `/start` 测试）
3. CHAT_ID是否正确（可以发送消息给 @userinfobot 获取）

### 如何获取Chat ID

1. 在Telegram中搜索 `@userinfobot`
2. 发送任意消息给它
3. 它会返回你的Chat ID

## 📊 数据持久化

Zeabur提供临时存储，重启后数据会丢失。建议：

1. **定期下载日志文件**: 每周下载一次 `btcv4_query_log.csv`
2. **使用外部存储**: 可以配置Zeabur持久化卷或连接云存储
3. **备份数据**: 定期备份历史数据和日志文件

## 🔄 更新部署

修改代码后：

**Git方式**: 推送到GitHub，Zeabur会自动重新部署

**CLI方式**:
```bash
zeabur deploy
```

## 📈 监控和维护

1. **查看日志**: 在Zeabur控制台查看实时日志
2. **资源监控**: Zeabur提供CPU、内存使用情况
3. **自动重启**: 如果Bot崩溃，Zeabur会自动重启服务

## 💡 最佳实践

1. **不要在代码中硬编码密钥**: 始终使用环境变量
2. **定期更新依赖**: 每月检查并更新Python包
3. **监控日志文件大小**: 定期清理或归档旧日志
4. **备份重要数据**: 定期下载CSV文件

## 📞 支持

如有问题，检查：
1. Zeabur控制台的日志输出
2. Telegram Bot是否正常响应
3. API密钥是否有效
