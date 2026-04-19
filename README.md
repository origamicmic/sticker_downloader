# Sticker Downloader Bot

一个 Telegram 贴纸下载机器人，可以帮助你下载 Telegram 贴纸并转换为常见格式。

## 主要功能

- 支持下载单个贴纸
- 支持下载整个贴纸包
- 自动转换 TGS 动画贴纸为 GIF 格式
- 自动转换 WebM 动画贴纸为 GIF 格式
- 处理静态贴纸的透明背景
- 支持查询使用次数

## 使用方法

1. 向机器人发送一个贴纸
2. 选择下载选项：
   - 「整个贴纸包」：下载整个贴纸包的所有贴纸
   - 「仅下载这张」：只下载当前发送的贴纸
3. 机器人会将贴纸转换为相应格式并发送给你
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
   git clone https://github.com/origamicmic/stickerdownloader_by_origamicmic.git
   cd stickerdownloader_by_origamicmic
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

### Docker 部署

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

## 注意事项

- 机器人使用内存存储用户数据，重启后会重置计数器
- 下载的贴纸会自动清理，不会占用磁盘空间
- 请遵守 Telegram 的使用条款和相关法律法规