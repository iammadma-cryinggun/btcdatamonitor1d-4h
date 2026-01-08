# 快速部署指南 - GitHub + Zeabur

## 🎯 目标仓库
https://github.com/iammadma-cryinggun/btcdatamonitor1d-4h

## 📋 部署准备

### 方案A：直接在部署目录初始化Git（推荐）

```bash
# 进入部署目录
cd "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署"

# 初始化Git
git init

# 添加远程仓库
git remote add origin https://github.com/iammadma-cryinggun/btcdatamonitor1d-4h.git

# 创建.gitignore
cat > .gitignore << EOF
.env
__pycache__/
*.pyc
*.log
*.pyc
btcv4_*_log.csv
.DS_Store
EOF

# 添加所有文件
git add .

# 提交
git commit -m "Deploy: BTC V4.0+V4.0.1 Hybrid Bot"

# 推送到GitHub（强制覆盖，请谨慎！）
git branch -M main
git push -u origin main --force
```

### 方案B：克隆到新目录

```bash
# 创建新目录
mkdir "C:\Users\Martin\GitHub\btcdatamonitor1d-4h"
cd "C:\Users\Martin\GitHub\btcdatamonitor1d-4h"

# 克隆仓库
git clone https://github.com/iammadma-cryinggun/btcdatamonitor1d-4h.git .

# 复制部署文件
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\btcv4_hybrid_telegram_bot.py" .
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\btc_v70_predator_engine_fixed.py" .
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\market_filter.py" .
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\requirements.txt" .
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\Dockerfile" .
copy "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署\btc_daily_ohlcv_2years.csv" .

# 创建.gitignore
cat > .gitignore << EOF
.env
__pycache__/
*.pyc
*.log
*.pyc
btcv4_*_log.csv
.DS_Store
EOF

# 提交并推送
git add .
git commit -m "Deploy: BTC V4.0+V4.0.1 Hybrid Bot"
git push
```

## ✅ 部署文件清单

确认以下文件已准备：

```
btcdatamonitor1d-4h/
├── btcv4_hybrid_telegram_bot.py      # ✅ 混合版主程序
├── btc_v70_predator_engine_fixed.py  # ✅ V7.0引擎
├── market_filter.py                   # ✅ 市场过滤器
├── requirements.txt                   # ✅ Python依赖
├── Dockerfile                         # ✅ Docker配置
├── btc_daily_ohlcv_2years.csv        # ✅ 历史数据
└── .gitignore                         # ✅ Git忽略文件
```

## 🚀 Zeabur部署

### 1. 登录Zeabur

访问: https://zeabur.com
- 使用GitHub账号登录
- 授权访问 `iammadma-cryinggun/btcdatamonitor1d-4h` 仓库

### 2. 创建项目

1. 点击 "New Project"
2. 选择 "Deploy from GitHub"
3. 选择 `btcdatamonitor1d-4h` 仓库
4. 选择分支: `main`

### 3. 配置环境变量

在Zeabur项目设置中添加：

| 变量名 | 值 |
|--------|-----|
| `TELEGRAM_TOKEN` | `8536935536:AAEm1rqdJ-Eo_Urd6-ISnlEYHgNF31M9Tf4` |
| `CHAT_ID` | `838429342` |
| `COINALYZE_API_KEY` | `cd4bfa05-9951-4916-b02a-e4f45f992bc0` |

### 4. 部署

点击 "Deploy" 按钮
- 等待2-3分钟
- 查看Logs确认启动成功

### 5. 验证

在Telegram发送:
```
/help
```

应该收到帮助信息。

## 📊 部署后监控

### 查看日志

Zeabur控制台 → 选择服务 → Logs标签

### 测试命令

```
/help      # 查看帮助
/status    # 查看混合状态
/1d        # V4.0日线诊断
/compare   # 对比两个系统
```

## ⚠️ 注意事项

1. **数据文件大小**: `btc_daily_ohlcv_2years.csv` 约500KB，Git上传可能慢
2. **首次推送**: 可能需要几分钟
3. **日志文件**: 建议定期下载，不要保存在Zeabur

## 🔄 更新部署

修改代码后：
```bash
git add .
git commit -m "Update: 描述"
git push
```

Zeabur会自动重新部署。

---

**准备好了吗？选择方案A或方案B开始部署！**
