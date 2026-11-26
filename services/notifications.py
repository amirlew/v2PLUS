
from config import logger


async def send_message(bot, chat_id, message, reply_markup=None):
    """ارسال پیام و مدیریت خطاهای احتمالی."""
    if bot is None or chat_id is None or not message:
        return False

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup
        )
        return True

    except Exception as error:
        logger.error(
            "Could not send message to %s: %s",
            chat_id,
            error
        )
        return False


async def notify_admins(bot, admin_ids, message):
    """ارسال پیام به تمام مدیران."""
    if not admin_ids:
        return False

    results = []

    for admin_id in admin_ids:
        result = await send_message(
            bot,
            admin_id,
            message
        )
        results.append(result)

    return all(results)


async def notify_user(bot, user_id, message):
    """ارسال پیام به یک کاربر."""
    return await send_message(
        bot,
        user_id,
        message
    )
