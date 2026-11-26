
from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection
from keyboards.admin import admin_menu
from utils.helpers import is_admin, audit


async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if not is_admin(user.id):
        await message.reply_text(
            "⛔ شما دسترسی مدیریت ندارید."
        )
        return

    with get_connection() as db:
        users = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        products = db.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        orders = db.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        revenue = db.execute(
            """
            SELECT COALESCE(SUM(-amount), 0)
            FROM transactions
            WHERE transaction_type = 'purchase'
            """
        ).fetchone()[0]

    audit(
        user.id,
        "open_admin_panel",
        "Opened admin dashboard"
    )

    await message.reply_text(
        "🛠 پنل مدیریت VitoPlus\n\n"
        f"👥 تعداد کاربران: {users}\n"
        f"📦 تعداد محصولات: {products}\n"
        f"🛍 تعداد سفارش‌ها: {orders}\n"
        f"💰 مجموع فروش تومانی ثبت‌شده: {revenue:,} تومان",
        reply_markup=admin_menu()
    )


async def admin_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if not is_admin(user.id):
        await message.reply_text("⛔ دسترسی غیرمجاز.")
        return

    with get_connection() as db:
        users = db.execute(
            """
            SELECT telegram_id, username, first_name,
                   is_banned, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()

    if not users:
        await message.reply_text(
            "هنوز کاربری ثبت نشده است."
        )
        return

    lines = ["👥 آخرین کاربران ثبت‌شده:\n"]

    for item in users:
        status = (
            "🚫 مسدود"
            if item["is_banned"]
            else "✅ فعال"
        )

        username = (
            f"@{item['username']}"
            if item["username"]
            else "ندارد"
        )

        lines.append(
            f"🆔 شناسه: {item['telegram_id']}\n"
            f"👤 نام: {item['first_name'] or '-'}\n"
            f"🔗 نام کاربری: {username}\n"
            f"📌 وضعیت: {status}\n"
            f"📅 عضویت: {item['created_at']}\n"
        )

    await message.reply_text("\n".join(lines))


async def admin_logs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if not is_admin(user.id):
        await message.reply_text("⛔ دسترسی غیرمجاز.")
        return

    with get_connection() as db:
        logs = db.execute(
            """
            SELECT admin_id, action, details, created_at
            FROM audit_logs
            ORDER BY id DESC
            LIMIT 15
            """
        ).fetchall()

    if not logs:
        await message.reply_text(
            "📜 هنوز گزارشی ثبت نشده است."
        )
        return

    lines = ["📜 آخرین فعالیت‌های مدیران:\n"]

    for log in logs:
        lines.append(
            f"👮 مدیر: {log['admin_id']}\n"
            f"⚙️ عملیات: {log['action']}\n"
            f"📝 جزئیات: {log['details'] or '-'}\n"
            f"📅 زمان: {log['created_at']}\n"
        )

    await message.reply_text("\n".join(lines))
