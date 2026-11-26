
from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection


async def get_required_channels():
    with get_connection() as db:
        channels = db.execute(
            """
            SELECT id, channel_id, channel_name,
                   is_permanent, expires_at
            FROM required_channels
            WHERE is_active = 1
              AND (
                  is_permanent = 1
                  OR expires_at IS NULL
                  OR datetime(expires_at) > datetime('now')
              )
            ORDER BY id ASC
            """
        ).fetchall()

    return channels


async def check_membership(bot, user_id: int) -> bool:
    channels = await get_required_channels()

    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=channel["channel_id"],
                user_id=user_id
            )

            if member.status in ("member", "administrator", "creator"):
                continue

            if member.status == "restricted" and getattr(
                member, "is_member", False
            ):
                continue

            return False

        except Exception:
            return False

    return True


async def check_required_channels(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return False

    is_member = await check_membership(
        context.bot,
        user.id
    )

    if not is_member:
        await message.reply_text(
            "⛔️ برای استفاده از ربات، ابتدا باید عضو "
            "تمام کانال‌های الزامی بشی."
        )
        return False

    return True
