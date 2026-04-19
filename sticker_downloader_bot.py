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
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

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
user_interactions = {}  # 每个用户的每分钟交互次数
bot_daily_count = 0      # 整个bot的每日调用次数
bot_last_reset_date = datetime.now().date()  # 上次重置日期
user_daily_usage = {}    # 每个用户的每日使用次数

# ====================== 临时文件管理 ======================
def create_temp_file(suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        return temp_file.name

# ====================== 速率限制 ======================
def _cleanup_user_data(user_id: int):
    """清理过期数据（ check_rate_limit 和 /limit 共用）"""
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
            del user_daily_usage[user_id]

def check_rate_limit(user_id: int, sticker_count: int = 1, check_only: bool = False):
    """检查速率限制"""
    global bot_daily_count
    _cleanup_user_data(user_id)
    today = datetime.now().date()

    # 全局每日限制
    if bot_daily_count + sticker_count > DAILY_LIMIT:
        return False, "今天已经不行惹😿达咩达咩"

    # 用户每日限制
    if user_id in user_daily_usage and user_daily_usage[user_id]['date'] == today:
        if user_daily_usage[user_id]['count'] + sticker_count > USER_DAILY_LIMIT:
            return False, "你今天已经用太多啦～明天再来喵😺"
    
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

# ====================== 转换函数 ======================
async def download_to_drive(file_id, context, suffix):
    """下载文件到临时目录"""
    new_file = await context.bot.get_file(file_id)
    file_path = create_temp_file(suffix)
    await new_file.download_to_drive(file_path)
    return file_path

# ====================== 贴纸处理 ======================
async def process_sticker(sticker, context):
    """处理贴纸"""
    temp_file_paths = []
    try:
        # 处理静态贴纸
        if sticker.is_animated:
            # 处理动画贴纸
            file_path = await download_to_drive(sticker.file_id, context, '.tgs')
            temp_file_paths.append(file_path)
            output_path = create_temp_file('.gif')
            temp_file_paths.append(output_path)
            # 这里可以添加转换逻辑
            return output_path, 'gif'
        else:
            # 处理静态贴纸
            file_path = await download_to_drive(sticker.file_id, context, '.png')
            temp_file_paths.append(file_path)
            return file_path, 'png'
    except Exception as e:
        logger.error(f"处理贴纸时出错: {e}", exc_info=True)
        return None, None
    finally:
        # 清理临时文件
        for path in temp_file_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass

# ====================== 命令处理 ======================
async def start(update: Update, context):
    """处理 /start 命令"""
    await update.message.reply_text(
        "你好呀～\n我是一个可以帮你下载 Telegram 贴纸的机器人！\n\n"+
        "使用方法：\n"+
        "1. 直接向我发送一个贴纸\n"+
        "2. 选择下载选项\n"+
        "3. 我会将贴纸转换为相应格式并发送给你\n\n"+
        "发送 /limit 命令可以查询今日已使用次数"
    )

async def limit(update: Update, context):
    """处理 /limit 命令"""
    user_id = update.message.from_user.id
    _cleanup_user_data(user_id)
    today = datetime.now().date()

    # 获取用户今日使用次数
    used = user_daily_usage.get(user_id, {}).get('count', 0)
    
    # 计算用户剩余次数
    user_remaining = USER_DAILY_LIMIT - used
    
    # 根据剩余次数发送不同的消息
    if user_remaining > 100:
        await update.message.reply_text(f"还有好多好多次喵😺不用担心w\n今日已使用{used}次！")
    else:
        await update.message.reply_text(f"今日已使用{used}次！")

async def handle_sticker(update: Update, context):
    """处理贴纸消息"""
    user_id = update.message.from_user.id
    
    # 检查限流（只检查，不增加计数）
    allowed, message = check_rate_limit(user_id, check_only=True)
    if not allowed:
        await update.message.reply_text(message)
        return

    sticker = update.message.sticker
    unique_id = str(uuid.uuid4())[:8]
    context.user_data[unique_id] = {'file_id': sticker.file_id, 'set_name': sticker.set_name}

    # 根据贴纸是否在贴纸包中，显示不同的按钮
    if sticker.set_name:
        keyboard = [
            [InlineKeyboardButton("整个贴纸包", callback_data=f"pack_{unique_id}")],
            [InlineKeyboardButton("仅下载这张", callback_data=f"single_{unique_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("选择下载选项喵~", reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("仅下载这张", callback_data=f"single_{unique_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("这是一个独立贴纸喵~", reply_markup=reply_markup)

async def button_callback(update: Update, context):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()

    # 解析回调数据
    data = query.data
    user_id = query.from_user.id

    # 检查限流
    allowed, message = check_rate_limit(user_id)
    if not allowed:
        await query.edit_message_text(text=message)
        return

    if data.startswith('single_'):
        # 下载单个贴纸
        unique_id = data.split('_')[1]
        if unique_id not in context.user_data:
            await query.edit_message_text(text="贴纸信息过期了呜，请重新发送贴纸")
            return

        sticker_data = context.user_data[unique_id]
        file_id = sticker_data['file_id']

        # 获取贴纸对象
        try:
            sticker = await context.bot.get_sticker(file_id)
            await send_single_sticker(query, context, sticker)
        except Exception as e:
            logger.error(f"获取贴纸时出错: {e}", exc_info=True)
            await query.edit_message_text(text="获取贴纸信息失败呜，请重试")

    elif data.startswith('pack_'):
        # 下载整个贴纸包
        unique_id = data.split('_')[1]
        if unique_id not in context.user_data:
            await query.edit_message_text(text="贴纸信息过期了呜，请重新发送贴纸")
            return

        sticker_data = context.user_data[unique_id]
        set_name = sticker_data['set_name']

        # 获取贴纸包
        try:
            sticker_set = await context.bot.get_sticker_set(set_name)
            await send_sticker_pack(query, context, sticker_set)
        except Exception as e:
            logger.error(f"获取贴纸包时出错: {e}", exc_info=True)
            await query.edit_message_text(text="获取贴纸包失败呜，请重试")

async def send_single_sticker(query, context, sticker):
    """发送单个贴纸"""
    processed_file = None
    try:
        # 处理贴纸
        processed_file, file_type = await process_sticker(sticker, context)
        if not processed_file:
            await query.edit_message_text(text="处理贴纸失败呜，请重试")
            return

        # 发送处理后的文件
        if file_type == 'gif':
            await context.bot.send_animation(
                chat_id=query.message.chat_id,
                animation=open(processed_file, 'rb'),
                caption="这是你要的贴纸喵～"
            )
        else:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=open(processed_file, 'rb'),
                caption="这是你要的贴纸喵～"
            )
        await query.edit_message_text(text="下载完成啦～")
    except Exception as e:
        logger.error(f"发送贴纸时出错: {e}", exc_info=True)
        await query.edit_message_text(text="发送贴纸失败呜，请重试")
    finally:
        # 清理临时文件
        if processed_file and os.path.exists(processed_file):
            try:
                os.unlink(processed_file)
            except Exception:
                pass

async def send_sticker_pack(query, context, sticker_set):
    """发送整个贴纸包"""
    zip_path = None
    try:
        # 创建临时 ZIP 文件
        zip_path = create_temp_file('.zip')

        # 下载并打包所有贴纸
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, sticker in enumerate(sticker_set.stickers):
                # 处理贴纸
                processed_file, file_type = await process_sticker(sticker, context)
                if not processed_file:
                    continue

                # 生成文件名
                filename = f"sticker_{i+1}.{file_type}"
                zipf.write(processed_file, filename)

                # 清理临时文件
                try:
                    os.unlink(processed_file)
                except Exception:
                    pass

        # 发送 ZIP 文件
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=open(zip_path, 'rb'),
            filename=f"{sticker_set.name}.zip",
            caption=f"这是 '{sticker_set.title}' 贴纸包喵～"
        )
        await query.edit_message_text(text="下载完成啦～")
    except Exception as e:
        logger.error(f"发送贴纸包时出错: {e}", exc_info=True)
        await query.edit_message_text(text="发送贴纸包失败呜，请重试")
    finally:
        # 清理临时文件
        if zip_path and os.path.exists(zip_path):
            try:
                os.unlink(zip_path)
            except Exception:
                pass

# ====================== 主函数 ======================
def main():
    """主函数"""
    if not bot_token:
        logger.error("❌ 请设置 TELEGRAM_BOT_TOKEN 环境变量")
        return

    application = Application.builder().token(bot_token).build()

    # 添加处理器
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('limit', limit))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    # 启动机器人
    logger.info("😸开始工作了喵～")
    application.run_polling()

if __name__ == '__main__':
    main()