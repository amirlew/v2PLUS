from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection


async def save_support_message(user_id, message_text, message_type="text", file_id=None):
    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO support_messages
            (telegram_id, message_text, message_type, file_id, is_from_admin)
            VALUES (?, ?, ?, ?, 0)
        """, (user_id, message_text, message_type, file_id))

        return cursor.lastrowid


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🎧 به پشتیبانی v2PLUS خوش آمدی.\n\n"
        "پیامت رو ارسال کن تا بررسی بشه."
    )


async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not message:
        return

    text = message.text or message.caption or ""

    file_id = None
    message_type = "text"

    if message.photo:
        file_id = message.photo[-1].file_id
        message_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        message_type = "document"

    await save_support_message(
        user.id,
        text,
        message_type,
        file_id
    )

    await message.reply_text(
        "✅ پیام شما ثبت شد. پشتیبانی به‌زودی پاسخ خواهد داد."
    )