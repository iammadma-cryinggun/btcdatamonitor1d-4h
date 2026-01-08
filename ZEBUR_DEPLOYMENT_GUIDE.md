# BTC混合Bot Zeabur部署完整指南

## 📦 部署文件清单

在部署到Zeabur之前，确认以下文件在同一目录：

```
部署/
├── btcv4_hybrid_telegram_bot.py      # 混合版主程序
├── btc_v70_predator_engine_fixed.py  # V7.0引擎
├── market_filter.py                   # 市场过滤器
├── requirements.txt                   # Python依赖（已更新）
├── Dockerfile                         # Docker配置（已更新）
├── btc_daily_ohlcv_2years.csv        # 历史数据（731天，约500KB）
└── ZEBUR_DEPLOYMENT_GUIDE.md         # 本文档
```

## 🚀 Zeabur部署步骤

### 步骤1：准备部署目录

**方案A：使用现有部署目录**
```bash
cd "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署"
```

确认目录中包含所有必需文件（已就绪✅）

**方案B：创建干净的Zeabur部署目录**
```bash
# 创建zeabur专用目录
mkdir "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\zeabur_deploy"
cd "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\zeabur_deploy"

# 复制必要文件
copy "..\部署\btcv4_hybrid_telegram_bot.py" .
copy "..\部署\btc_v70_predator_engine_fixed.py" .
copy "..\部署\market_filter.py" .
copy "..\部署\requirements.txt" .
copy "..\部署\Dockerfile" .
copy "..\部署\btc_daily_ohlcv_2years.csv" .
```

### 步骤2：推送到GitHub

#### 2.1 初始化Git仓库（如果还没有）

```bash
cd "C:\Users\Martin\Downloads\机器人\趋势判断\实时数据监控\部署"

# 初始化Git
git init

# 创建.gitignore
echo ".env" > .gitignore
echo "__pycache__" >> .gitignore
echo "*.pyc" >> .gitignore
echo "*.log" >> .gitignore
echo "btcv4_*_log.csv" >> .gitignore

# 添加所有文件
git add .

# 提交
git commit -m "Deploy BTC V4.0+V4.0.1 Hybrid Bot to Zeabur"
```

#### 2.2 创建GitHub仓库

1. 访问 https://github.com/new
2. 仓库名称: `btc-hybrid-bot-zeabur`
3. 设为**私有**（Private，推荐）或公开
4. 不要初始化README、.gitignore或LICENSE

#### 2.3 推送到GitHub

```bash
# 添加远程仓库
git remote add origin https://github.com/你的用户名/btc-hybrid-bot-zeabur.git

# 推送
git branch -M main
git push -u origin main
```

### 步骤3：在Zeabur中部署

#### 3.1 登录Zeabur

1. 访问 https://zeabur.com
2. 使用GitHub账号登录
3. 授权Zeabur访问你的GitHub仓库

#### 3.2 创建新项目

1. 点击 "New Project"
2. 选择 "Deploy from GitHub"
3. 选择 `btc-hybrid-bot-zeabur` 仓库

#### 3.3 配置服务

Zeabur会自动检测Python项目，配置如下：

**基础配置**:
- **Service Name**: `btc-hybrid-bot`
- **Region**: 选择离你最近的区域（如 Hong Kong 或 Singapore）
- **Branch**: `main`

**环境变量**（必需）:

点击 "Variables" 添加以下环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `TELEGRAM_TOKEN` | `8536935536:AAEm1rqdJ-Eo_Urd6-ISnlEYHgNF31M9Tf4` | Telegram Bot Token |
| `CHAT_ID` | `838429342` | 你的Chat ID |
| `COINALYZE_API_KEY` | `cd4bfa05-9951-4916-b02a-e4f45f992bc0` | Coinalyze API密钥 |

**重要提示**:
- ✅ 不要在代码中硬编码这些密钥
- ✅ 使用环境变量，更安全
- ✅ 这些配置会自动注入到容器中

#### 3.4 启动部署

1. 点击 "Deploy"
2. Zeabur会自动：
   - 构建 Docker 镜像
   - 安装 Python 依赖
   - 启动混合Bot
3. 等待部署完成（约2-3分钟）

### 步骤4：验证部署

#### 4.1 查看日志

在Zeabur控制台：
1. 点击你的服务 `btc-hybrid-bot`
2. 查看 "Logs" 标签
3. 应该看到类似的输出：

```
==========================================
BTC V4.0 + V4.0.1 混合Bot启动中...
==========================================
[OK] 历史数据加载完成: 731 天
[OK] V4.0系统初始化完成
[OK] V4.0.1系统初始化完成
[OK] 混合Bot已启动，可以接收命令了
[OK] 定时任务：每天UTC 0:00自动运行两个系统
```

#### 4.2 测试Telegram命令

在你的Telegram中发送：

```
/help
```

应该收到帮助信息。

再测试：
```
/status
```

应该收到混合系统状态报告。

#### 4.3 测试V4.0命令

```
/1d
```

应该收到V4.0日线诊断。

## 📊 部署后管理

### 查看实时日志

在Zeabur控制台：
1. 选择服务
2. 点击 "Logs" 标签
3. 实时查看Bot运行日志

### 下载日志文件

Zeabur提供临时存储，但**建议定期下载日志**：

#### 方法1：通过Zeabur控制台

1. 进入服务的 "Terminal" 标签
2. 使用命令下载：

```bash
# 列出日志文件
ls -lh *.csv

# 下载V4.0日志（在浏览器中）
cat btcv4_query_log.csv

# 下载V4.0.1日志
cat btcv4_1_alert_log.csv
```

#### 方法2：持久化存储（推荐）

**配置Zeabur持久化卷**：
1. 在Zeabur控制台，选择服务
2. 点击 "Storage" 标签
3. 添加持久化卷：
   - 路径: `/app/data`
   - 大小: 1GB

**修改代码保存日志到持久化目录**：

```python
# 在 btcv4_hybrid_telegram_bot.py 中修改
self.log_file = 'data/btcv4_query_log.csv'  # V4.0
self.log_file = 'data/btcv4_1_alert_log.csv'  # V4.0.1
```

重新部署后，日志会持久保存。

### 监控资源使用

在Zeabur控制台：
- **CPU使用率**: 监控Bot的计算资源
- **内存使用**: 确保不超过512MB
- **网络流量**: 监控API请求

### 更新部署

修改代码后：

```bash
# 本地提交
git add .
git commit -m "Update: 添加新功能"
git push

# Zeabur会自动检测并重新部署
```

## 🔧 故障排查

### 问题1：部署失败

**症状**: Zeabur显示 "Build Failed"

**解决**:
1. 检查 "Build Logs" 查看详细错误
2. 常见原因：
   - `requirements.txt` 格式错误
   - Python版本不兼容
   - 文件路径错误

### 问题2：Bot启动失败

**症状**: 部署成功但Bot无响应

**解决**:
1. 查看 "Logs" 检查启动错误
2. 常见原因：
   - 环境变量未设置
   - `btc_daily_ohlcv_2years.csv` 缺失
   - Telegram Token错误

### 问题3：定时任务不执行

**症状**: 每天UTC 0:00没有收到报告

**解决**:
1. 检查 `python-telegram-bot[job-queue]` 是否正确安装
2. 查看 Logs 确认定时任务已注册
3. 确认Bot持续运行（未被重启）

### 问题4：数据文件过大

**症状**: Zeabur提示存储空间不足

**解决**:
1. 定期下载并删除旧日志
2. 使用持久化存储
3. 限制日志文件大小：

```python
# 在日志记录前检查文件大小
if os.path.exists(self.log_file):
    size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
    if size_mb > 10:  # 超过10MB
        # 备份并创建新文件
        os.rename(self.log_file, f"{self.log_file}.bak")
```

## 💡 最佳实践

### 1. 定期备份

**每周一次**：
1. 下载两个日志文件
2. 保存到本地或Google Drive
3. 清理Zeabur中的旧日志

### 2. 监控准确性

**每月一次**：
1. 下载日志文件
2. 在Excel中打开
3. 手动填写 `actual_outcome` 列
4. 对比V4.0和V4.0.1的准确率

### 3. 更新依赖

**每季度一次**：
```bash
# 更新requirements.txt中的版本号
# 测试本地运行
# 推送到GitHub触发自动部署
```

### 4. 安全检查

**定期检查**：
- ✅ Telegram Token未泄露
- ✅ Coinalyze API密钥有效
- ✅ 日志文件不包含敏感信息

## 📈 成本优化

Zeabur免费套餐：
- ✅ 每月一定量的免费运行时间
- ✅ 512MB内存
- ✅ 足够运行混合Bot

如果超出免费额度：
- 考虑升级到付费计划
- 或使用其他平台（如Railway, Render）

## 🔄 回滚到V4.0

如果需要切换回V4.0：

```bash
# 修改Dockerfile
# 将 btcv4_hybrid_telegram_bot.py 改回 btcv4_telegram_bot.py

git add Dockerfile
git commit -m "Rollback to V4.0"
git push
```

## 📞 技术支持

如有问题：
1. 查看Zeabur文档: https://zeabur.com/docs
2. 检查GitHub Issues
3. 查看Bot日志

---

**部署状态**: ✅ 准备就绪

**下一步**:
1. 推送代码到GitHub
2. 在Zeabur中部署
3. 测试Telegram命令
4. 等待第2天UTC 0:00的自动报告

**预期运行时间**: 7x24小时持续运行

**日志监控**: 建议每周下载一次日志文件
