FROM python:3.10-slim

# 安装 ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app

# 安装依赖
RUN pip install --no-cache-dir python-telegram-bot Pillow ffmpeg-python

# 运行机器人
CMD ["python", "sticker_downloader_bot.py"]