
from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection
from utils.helpers import back_menu


async def show_wallet(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    with get_connection() as db:
        result = db.execute(
            """
            SELECT wallet_balance
            FROM users
            WHERE telegram_id = ?
              AND is_banned = 0
            """,
            (user.id,)
        ).fetchone()

        toman_setting = db.execute(
            """
            SELECT setting_value
            FROM settings
            WHERE setting_key = 'toman_payment_enabled'
            """
        ).fetchone()

    if result is None:
        await message.reply_text(
            "❌ حساب کاربری پیدا نشد یا دسترسی آن غیرفعال است."
        )
        return

    balance = result["wallet_balance"] or 0
    toman_enabled = (
        toman_setting is not None
        and toman_setting["setting_value"] == "1"
    )

    payment_status = (
        "✅ فعال"
        if toman_enabled
        else "🔒 در حال حاضر غیرفعال"
    )

    await message.reply_text(
        "💰 کیف پول VitoPlus\n\n"
        f"💵 موجودی فعلی: {balance:,} تومان\n"
        f"💳 امکان شارژ تومانی: {payment_status}\n\n"
        "برای مشاهده جزئیات تراکنش‌ها از بخش تراکنش‌ها استفاده کن.",
        reply_markup=back_menu()
    )


async def get_wallet_balance(user_id: int) -> int:
    with get_connection() as db:
        result = db.execute(
            """
            SELECT wallet_balance
            FROM users
            WHERE telegram_id = ?
            """,
            (user_id,)
        ).fetchone()

    if result is None:
        return 0

    return result["wallet_balance"] or 0
