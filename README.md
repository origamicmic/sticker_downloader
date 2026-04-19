# Sticker Downloader Bot

一个Telegram贴纸下载机器人

## 主要功能

- 支持下载整个贴纸包和单个贴纸
- 自动转换动画贴纸为GIF格式
- 自动将透明背景的静态贴纸处理为白色背景

## 使用方法

1. 直接向机器人发送贴纸
2. 选择下载选项：
   - 「整个贴纸包」：下载整个贴纸包的所有贴纸
   - 「仅下载这张」：只下载当前发送的贴纸
3. 机器人会进行处理并返回相应的PNG/GIF格式图片
4. 发送 `/limit` 命令可以查询今日已使用次数

## 自行部署

### 环境要求

- Python 3.10+
- ffmpeg
- 以下 Python 包：
  - python-telegram-bot
  - Pillow
  - ffmpeg-python

### 部署步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/origamicmic/sticker_downloader.git
   cd sticker_downloader
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量：
   - `TELEGRAM_BOT_TOKEN`：你的 Telegram Bot Token
   - `MINUTE_LIMIT`：每分钟最大调用次数（可选，默认 10）
   - `DAILY_LIMIT`：每日最大调用次数（可选，默认 2000）
   - `USER_DAILY_LIMIT`：每个用户每日最大调用次数（可选，默认 2000）

4. 运行机器人：
   ```bash
   python sticker_downloader_bot.py
   ```

## 关于依赖的平台部署

### 部分telegrambot托管平台不预装项目所需的依赖，如需托管至平台，可 Docker 部署

1. 构建 Docker 镜像：
   ```bash
   docker build -t sticker-downloader-bot .
   ```

2. 运行容器：
   ```bash
   docker run -d --name sticker-downloader-bot \
     -e TELEGRAM_BOT_TOKEN=your_bot_token \
     -e MINUTE_LIMIT=10 \
     -e DAILY_LIMIT=2000 \
     -e USER_DAILY_LIMIT=2000 \
     sticker-downloader-bot
   ```

## 其他
- 下载的贴纸会自动清理，不会占用磁盘空间
- 使用时请遵守Telegram的使用条款和相关法律法规