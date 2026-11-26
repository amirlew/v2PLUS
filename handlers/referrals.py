
from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection


async def get_referral_link(bot, user_id):
    bot_info = await bot.get_me()

    return (
        f"https://t.me/{bot_info.username}"
        f"?start=ref_{user_id}"
    )


async def get_referral_count(user_id):
    with get_connection() as db:
        result = db.execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE referred_by = ?
            """,
            (user_id,)
        ).fetchone()

    return result[0] if result else 0


async def referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    link = await get_referral_link(
        context.bot,
        user.id
    )

    count = await get_referral_count(user.id)

    with get_connection() as db:
        setting = db.execute(
            """
            SELECT setting_value
            FROM settings
            WHERE setting_key = 'referral_reward'
            """
        ).fetchone()

    reward = setting["setting_value"] if setting else "0"

    await message.reply_text(
        "🎁 سیستم زیرمجموعه‌گیری VitoPlus\n\n"
        f"👥 تعداد افراد دعوت‌شده: {count}\n"
        f"💰 پاداش هر دعوت: {reward} تومان\n\n"
        "🔗 لینک اختصاصی دعوت شما:\n"
        f"{link}\n\n"
        "این لینک رو برای دوستانت ارسال کن."
    )


async def register_referral(new_user_id, referrer_id):
    if new_user_id == referrer_id:
        return False

    with get_connection() as db:
        new_user = db.execute(
            """
            SELECT referred_by
            FROM users
            WHERE telegram_id = ?
            """,
            (new_user_id,)
        ).fetchone()

        referrer = db.execute(
            """
            SELECT telegram_id
            FROM users
            WHERE telegram_id = ?
              AND is_banned = 0
            """,
            (referrer_id,)
        ).fetchone()

        if new_user is None or referrer is None:
            return False

        if new_user["referred_by"] is not None:
            return False

        db.execute(
            """
            UPDATE users
            SET referred_by = ?
            WHERE telegram_id = ?
            """,
            (referrer_id, new_user_id)
        )

        return True
