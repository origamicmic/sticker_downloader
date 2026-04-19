"""
Name: sticker downloader
Version: 1.0.0
Developer: https://github.com/origamicmic
"""
import os
import tempfile
import zipfile
import uuid
import logging
import subprocess
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from PIL import Image

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: Application):
    """全局错误处理器"""
    logger.error(f"❌ 处理update时发生错误: {context.error}", exc_info=True)

    if update and hasattr(update, "message") and update.message:
        try:
            await update.message.reply_text("喵呜出错了抱歉😿\n请联系咱的主人或稍后再试喵~")
        except:
            pass

# 从环境变量获取配置（云端部署）
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')                   # 请在@Botfather处获取token并填入TELEGRAM_BOT_TOKEN
MINUTE_LIMIT = int(os.environ.get('MINUTE_LIMIT', 10))             # 默认每分钟最多10次
DAILY_LIMIT = int(os.environ.get('DAILY_LIMIT', 2000))             # 默认每天最多2000张
USER_DAILY_LIMIT = int(os.environ.get('USER_DAILY_LIMIT', 2000))   # 默认每个用户每天最多2000张

# 全局计数器
user_interactions = {}                                             # 每个用户的每分钟交互次数
bot_daily_count = 0                                                # bot的全局每日调用次数
bot_last_reset_date = datetime.now().date()                        # 上次重置日期
user_daily_usage = {}                                              # 每个用户的每日使用次数 

# ====================== 临时文件管理 ======================
def create_temp_file(suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        return temp_file.name

# ====================== 速率限制 ======================
def _cleanup_user_data(user_id: int):
    """清理过期数据（check_rate_limit和/limit共用）"""
    global bot_daily_count, bot_last_reset_date
    now = datetime.now()
    today = now.date()

    # 重置全局每日计数器
    if today != bot_last_reset_date:
        bot_daily_count = 0
        bot_last_reset_date = today

    # 清理用户的每分钟交互记录
    if user_id in user_interactions:
        user_interactions[user_id] = [t for t in user_interactions[user_id] if now - t < timedelta(minutes=1)]
        if not user_interactions[user_id]:
            del user_interactions[user_id]

    # 清理用户的每日使用记录
    if user_id in user_daily_usage:
        if today != user_daily_usage[user_id]['date']:
            user_daily_usage[user_id] = {'date': today, 'count': 0}

def check_rate_limit(user_id: int, sticker_count: int = 1, check_only: bool = False):
    global bot_daily_count
    _cleanup_user_data(user_id)
    today = datetime.now().date()

    # 全局每日限制
    if bot_daily_count + sticker_count > DAILY_LIMIT:
        return False, "今天已经不行惹😿达咩达咩"

    # 用户每日限制
    if user_id in user_daily_usage and user_daily_usage[user_id]['date'] == today:
        if user_daily_usage[user_id]['count'] + sticker_count > USER_DAILY_LIMIT:
            return False, "今天已经不行惹😿达咩达咩"
    
    # 每分钟限制
    if user_id not in user_interactions:
        user_interactions[user_id] = [datetime.now()]
    else:
        if len(user_interactions[user_id]) + 1 > MINUTE_LIMIT:
            return False, "你急个damn😾等会喵"
        if not check_only:
            user_interactions[user_id].append(datetime.now())

    # 如果只是检查，不更新计数
    if check_only:
        return True, None

    # 更新全局每日计数
    bot_daily_count += sticker_count

    # 更新用户每日使用记录
    if user_id not in user_daily_usage:
        user_daily_usage[user_id] = {'date': today, 'count': sticker_count}
    else:
        user_daily_usage[user_id]['count'] += sticker_count

    return True, None

# ====================== 转换 & 处理函数 ======================
def convert_tgs_to_gif(tgs_path, gif_path):
    try:
        import lottie
        from lottie.exporters import export_gif
        from lottie.parsers.tgs import parse_tgs
        animation = parse_tgs(tgs_path)
        export_gif(animation, gif_path, 512, 512, 30)
        return True
    except Exception as e:
        logger.error(f"TGS转GIF失败: {str(e)}")
        return False

def convert_webm_to_gif(webm_path, gif_path):
    try:
        import subprocess
        cmd = ['ffmpeg', '-i', webm_path, '-vf', 'scale=512:-1', '-pix_fmt', 'rgb24', '-loop', '0', '-y', gif_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and os.path.exists(gif_path) and os.path.getsize(gif_path) > 0
    except Exception as e:
        logger.error(f"WebM转GIF失败: {str(e)}")
        return False

def handle_transparent_background(image_path):
    try:
        from PIL import Image
        img = Image.open(image_path)

        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # 标准白色背景处理
            if img.mode == 'P':
                img = img.convert('RGBA')
            alpha = img.split()[-1]
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img.convert('RGB'), (0, 0), alpha)
            img = background
        else:
            img = img.convert('RGB')

        img.save(image_path, 'PNG')
        return True
    except Exception as e:
        logger.error(f"透明背景处理失败: {str(e)}")
        return False

async def process_sticker(file_id, context):
    """处理单张贴纸，返回最终文件路径"""
    file = await context.bot.get_file(file_id)
    file_path = file.file_path
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension in ['.tgs', '.webm']:
        temp_original = create_temp_file(file_extension)
        await file.download_to_drive(temp_original)

        temp_gif = create_temp_file('.gif')
        success = False
        if file_extension == '.tgs':
            success = convert_tgs_to_gif(temp_original, temp_gif)
        elif file_extension == '.webm':
            success = convert_webm_to_gif(temp_original, temp_gif)

        if success:
            os.unlink(temp_original)      # 删除原始动画文件
            return temp_gif
        else:
            os.unlink(temp_gif)           # 删除失败的GIF
            return temp_original          # 返回原始文件

    else:
        # 静态贴纸PNG处理
        png_path = create_temp_file('.png')
        await file.download_to_drive(png_path)
        handle_transparent_background(png_path)
        return png_path

# ====================== Bot 命令 & 处理 ======================
async def start(update: Update, context):
    await update.message.reply_text('Ciallo～(∠・ω< )⌒★\n直接发送贴纸给咱就可以了喵😼')

async def limit(update: Update, context):
    user_id = update.message.from_user.id
    _cleanup_user_data(user_id)   # 复用清理逻辑
    today = datetime.now().date()
    
    # 获取用户今日使用次数
    if user_id in user_daily_usage and user_daily_usage[user_id]['date'] == today:
        used = user_daily_usage[user_id]['count']
    else:
        used = 0
    
    # 计算用户剩余次数
    user_remaining = USER_DAILY_LIMIT - used
    
    # 根据剩余次数发送不同的消息
    if user_remaining > 100:
        await update.message.reply_text(f"还有好多好多次喵😺不用担心w\n今日已使用{used}次！")
    else:
        await update.message.reply_text(f"今日已使用{used}次！")

async def handle_sticker(update: Update, context):
    user_id = update.message.from_user.id
    
    # 检查限流（只检查，不增加计数）
    allowed, message = check_rate_limit(user_id, check_only=True)
    if not allowed:
        await update.message.reply_text(message)
        return

    sticker = update.message.sticker
    unique_id = str(uuid.uuid4())[:8]
    context.user_data[unique_id] = {'file_id': sticker.file_id, 'set_name': sticker.set_name}

    if sticker.set_name:
        keyboard = [[InlineKeyboardButton("📁整个贴纸包", callback_data=f"pack_{unique_id}"),
                     InlineKeyboardButton("🖼仅下载这张", callback_data=f"single_{unique_id}")]]
        text = "是否下载该贴纸所在的整个贴纸包？"
    else:
        keyboard = [[InlineKeyboardButton("🖼仅下载这张", callback_data=f"single_{unique_id}")]]
        text = "选择操作："

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_single_sticker(file_id, update, context):
    processed_file = None
    try:
        await update.callback_query.edit_message_text("正在处理中😼稍等喵...")
        processed_file = await process_sticker(file_id, context)

        await update.callback_query.delete_message()

        if processed_file.endswith('.gif'):
            with open(processed_file, 'rb') as f:
                await update.callback_query.message.reply_animation(animation=f)
        else:
            with open(processed_file, 'rb') as f:
                await update.callback_query.message.reply_photo(photo=f)
    except Exception as e:
        await update.callback_query.edit_message_text(f"处理失败：{str(e)}")
    finally:
        if processed_file and os.path.exists(processed_file):
            try:
                os.unlink(processed_file)
            except:
                pass

async def send_sticker_pack(pack_name, update, context):
    zip_path = None
    try:
        await update.callback_query.edit_message_text("正在处理中😼稍等喵...")
        stickers = await context.bot.get_sticker_set(pack_name)

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            zip_path = temp_zip.name

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, sticker in enumerate(stickers.stickers):
                processed_file = await process_sticker(sticker.file_id, context)
                new_name = f"sticker_{i+1}{os.path.splitext(processed_file)[1]}"
                zipf.write(processed_file, new_name)
                os.unlink(processed_file)

        await update.callback_query.delete_message()
        with open(zip_path, 'rb') as f:
            await update.callback_query.message.reply_document(document=f, filename=f"sticker_pack_{pack_name}.zip")
    except Exception as e:
        await update.callback_query.edit_message_text(f"处理失败：{str(e)}")
    finally:
        if zip_path and os.path.exists(zip_path):
            try:
                os.unlink(zip_path)
            except:
                pass

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    callback_data = query.data
    user_id = query.from_user.id

    if callback_data.startswith('pack_'):
        unique_id = callback_data.split('pack_')[1]
        if unique_id in context.user_data:
            pack_name = context.user_data[unique_id]['set_name']
            try:
                stickers = await context.bot.get_sticker_set(pack_name)
                allowed, msg = check_rate_limit(user_id, len(stickers.stickers))
                if not allowed:
                    await query.edit_message_text(text=msg)
                    return
                await send_sticker_pack(pack_name, update, context)
            except Exception as e:
                logger.error(f"获取贴纸包失败: {str(e)}")
                await query.edit_message_text(text="获取贴纸包时出错了呜😿请稍后再试")
        else:
            await query.edit_message_text(text="贴纸信息过期了呜😿重新发给咱吧喵！")

    elif callback_data.startswith('single_'):
        unique_id = callback_data.split('single_')[1]
        if unique_id in context.user_data:
            file_id = context.user_data[unique_id]['file_id']
            allowed, msg = check_rate_limit(user_id)
            if not allowed:
                await query.edit_message_text(text=msg)
                return
            await send_single_sticker(file_id, update, context)
        else:
            await query.edit_message_text(text="贴纸信息过期了呜😿重新发给咱吧喵！")

def main():
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('limit', limit))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    logger.info("😸开始工作了喵～")
    application.run_polling()

if __name__ == '__main__':
    main()