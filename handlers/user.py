
from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection
from utils.helpers import back_menu


async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    with get_connection() as db:
        result = db.execute(
            """
            SELECT telegram_id, username, first_name,
                   wallet_balance, is_banned, created_at
            FROM users
            WHERE telegram_id = ?
            """,
            (user.id,)
        ).fetchone()

    if not result:
        await message.reply_text(
            "❌ حساب کاربری پیدا نشد. لطفاً /start را ارسال کنید."
        )
        return

    status = "⛔ مسدود" if result["is_banned"] else "✅ فعال"
    username = f"@{result['username']}" if result["username"] else "ندارد"
    balance = result["wallet_balance"] or 0

    await message.reply_text(
        "👤 اطلاعات حساب کاربری شما\n\n"
        f"🆔 شناسه تلگرام: {result['telegram_id']}\n"
        f"👤 نام: {result['first_name'] or '-'}\n"
        f"🔗 نام کاربری: {username}\n"
        f"💰 موجودی کیف پول: {balance:,} تومان\n"
        f"📌 وضعیت حساب: {status}\n"
        f"📅 تاریخ عضویت: {result['created_at'] or '-'}",
        reply_markup=back_menu()
    )


async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    with get_connection() as db:
        rows = db.execute(
            """
            SELECT id, amount, transaction_type,
                   description, created_at
            FROM transactions
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (user.id,)
        ).fetchall()

    if not rows:
        await message.reply_text(
            "💳 هنوز هیچ تراکنشی برای حساب شما ثبت نشده است.",
            reply_markup=back_menu()
        )
        return

    lines = ["💳 آخرین تراکنش‌های شما:\n"]

    for item in rows:
        amount = item["amount"] or 0
        sign = "+" if amount > 0 else ""

        lines.append(
            f"🔹 تراکنش شماره {item['id']}\n"
            f"💰 مبلغ: {sign}{amount:,} تومان\n"
            f"📌 نوع: {item['transaction_type']}\n"
            f"📝 توضیحات: {item['description'] or '-'}\n"
            f"📅 تاریخ: {item['created_at'] or '-'}\n"
        )

    await message.reply_text(
        "\n".join(lines),
        reply_markup=back_menu()
    )
