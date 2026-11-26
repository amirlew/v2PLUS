
from telegram import Update
from telegram.ext import ContextTypes

from database import get_connection
from utils.helpers import is_admin, back_menu, admin_back


async def user_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    with get_connection() as db:
        orders = db.execute(
            """
            SELECT
                o.id,
                o.volume_gb,
                o.price,
                o.status,
                o.payment_method,
                o.created_at,
                o.expires_at,
                p.name AS product_name
            FROM orders o
            LEFT JOIN products p ON p.id = o.product_id
            WHERE o.telegram_id = ?
            ORDER BY o.id DESC
            LIMIT 10
            """,
            (user.id,)
        ).fetchall()

    if not orders:
        await message.reply_text(
            "📦 هنوز هیچ سفارشی ثبت نکرده‌ای.",
            reply_markup=back_menu()
        )
        return

    lines = ["📦 آخرین سفارش‌های شما:\n"]

    for order in orders:
        product_name = order["product_name"] or "محصول حذف‌شده"
        payment_method = order["payment_method"] or "ثبت نشده"
        expires_at = order["expires_at"] or "ثبت نشده"
        price = order["price"] or 0

        lines.append(
            f"🔹 سفارش شماره {order['id']}\n"
            f"📦 محصول: {product_name}\n"
            f"📊 حجم: {order['volume_gb']} گیگابایت\n"
            f"💰 مبلغ: {price:,} تومان\n"
            f"💳 روش پرداخت: {payment_method}\n"
            f"📌 وضعیت: {order['status']}\n"
            f"📅 تاریخ ثبت: {order['created_at']}\n"
            f"⏳ انقضا: {expires_at}\n"
        )

    await message.reply_text(
        "\n".join(lines),
        reply_markup=back_menu()
    )


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):
        await message.reply_text("⛔ دسترسی غیرمجاز.")
        return

    with get_connection() as db:
        orders = db.execute(
            """
            SELECT
                o.id,
                o.telegram_id,
                o.volume_gb,
                o.price,
                o.status,
                o.payment_method,
                o.created_at,
                p.name AS product_name
            FROM orders o
            LEFT JOIN products p ON p.id = o.product_id
            ORDER BY o.id DESC
            LIMIT 20
            """
        ).fetchall()

    if not orders:
        await message.reply_text(
            "📦 هنوز سفارشی در ربات ثبت نشده است.",
            reply_markup=admin_back()
        )
        return

    lines = ["🛍 آخرین سفارش‌های ثبت‌شده:\n"]

    for order in orders:
        product_name = order["product_name"] or "محصول حذف‌شده"
        price = order["price"] or 0

        lines.append(
            f"🔹 سفارش شماره {order['id']}\n"
            f"👤 شناسه کاربر: {order['telegram_id']}\n"
            f"📦 محصول: {product_name}\n"
            f"📊 حجم: {order['volume_gb']} گیگابایت\n"
            f"💰 مبلغ: {price:,} تومان\n"
            f"💳 روش پرداخت: {order['payment_method'] or '-'}\n"
            f"📌 وضعیت: {order['status']}\n"
            f"📅 تاریخ: {order['created_at']}\n"
        )

    await message.reply_text(
        "\n".join(lines),
        reply_markup=admin_back()
    )
