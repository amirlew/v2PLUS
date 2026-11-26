import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from config import BOT_TOKEN, logger
from database import initialize_database, get_connection
from utils.helpers import register_user, is_admin, main_menu, audit

from handlers.admin import admin_panel, admin_logs
from handlers.orders import user_orders, admin_orders
from handlers.products import show_products, show_product
from handlers.referrals import referrals, register_referral
from handlers.stars import buy_with_stars, pre_checkout, successful_payment
from handlers.support import support, handle_support_message
from handlers.user import account, transactions
from handlers.wallet import show_wallet

from services.products import (
    get_all_products,
    get_product_details,
    update_product,
    set_product_active,
    set_product_stock,
)
from services.statistics import get_dashboard_statistics
from services.users import get_all_users, set_user_ban
from services.admin_tools import get_active_admins


# ----------------------------- Commands -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    register_user(user)

    if context.args and context.args[0].startswith("ref_"):
        try:
            await register_referral(user.id, int(context.args[0][4:]))
        except (TypeError, ValueError):
            logger.info("Invalid referral argument from user %s", user.id)

    with get_connection() as db:
        row = db.execute(
            "SELECT is_banned FROM users WHERE telegram_id = ?",
            (user.id,),
        ).fetchone()

    if row and row["is_banned"]:
        await message.reply_text("⛔ حساب کاربری شما مسدود شده است.")
        return

    context.user_data.clear()
    await message.reply_text(
        f"سلام {user.first_name or 'دوست عزیز'}! 👋\n\n"
        "به VitoPlus خوش اومدی.\nاز منوی زیر بخش موردنظرت رو انتخاب کن:",
        reply_markup=main_menu(),
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_panel(update, context)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_text(
            "عملیات لغو شد.", reply_markup=main_menu()
        )


# ----------------------------- Admin screens -----------------------------

async def show_admin_products(message):
    products = get_all_products()
    if not products:
        await message.reply_text(
            "هنوز محصولی ثبت نشده است.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")
            ]]),
        )
        return

    rows = []
    for product in products[:40]:
        status = "🟢" if product["is_active"] else "⚪"
        rows.append([InlineKeyboardButton(
            f"{status} {product['name']} | {product['volume_gb']}GB",
            callback_data=f"admin_product_{product['id']}",
        )])
    rows.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")])
    await message.reply_text("📦 مدیریت محصولات\nمحصول موردنظر را انتخاب کن:",
                             reply_markup=InlineKeyboardMarkup(rows))


async def show_admin_product(message, product_id):
    product = get_product_details(product_id)
    if not product:
        await message.reply_text("محصول پیدا نشد.")
        return

    status = "فعال" if product["is_active"] else "غیرفعال"
    text = (
        f"📦 {product['name']}\n\n"
        f"شناسه: {product['id']}\n"
        f"نوع: {product['product_type']}\n"
        f"حجم: {product['volume_gb']} گیگابایت\n"
        f"قیمت تومانی: {product['price']:,}\n"
        f"قیمت Stars: {product['stars_price']}\n"
        f"موجودی: {product['stock']}\n"
        f"وضعیت: {status}"
    )
    keyboard = [
        [
            InlineKeyboardButton("✏️ ویرایش قیمت", callback_data=f"edit_price_{product_id}"),
            InlineKeyboardButton("📦 ویرایش موجودی", callback_data=f"edit_stock_{product_id}"),
        ],
        [InlineKeyboardButton(
            "⏸ غیرفعال کردن" if product["is_active"] else "▶️ فعال کردن",
            callback_data=f"toggle_product_{product_id}",
        )],
        [InlineKeyboardButton("🔙 فهرست محصولات", callback_data="admin_products")],
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_admin_users(message):
    users = get_all_users(limit=20)
    if not users:
        await message.reply_text("هنوز کاربری ثبت نشده است.")
        return

    rows = []
    for item in users:
        name = item["first_name"] or str(item["telegram_id"])
        mark = "🚫" if item["is_banned"] else "👤"
        rows.append([InlineKeyboardButton(
            f"{mark} {name} ({item['telegram_id']})",
            callback_data=f"admin_user_{item['telegram_id']}",
        )])
    rows.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")])
    await message.reply_text("👥 انتخاب کاربر:", reply_markup=InlineKeyboardMarkup(rows))


async def show_admin_user(message, user_id):
    with get_connection() as db:
        item = db.execute(
            "SELECT telegram_id, username, first_name, wallet_balance, is_banned "
            "FROM users WHERE telegram_id = ?",
            (user_id,),
        ).fetchone()
    if not item:
        await message.reply_text("کاربر پیدا نشد.")
        return

    status = "مسدود" if item["is_banned"] else "فعال"
    username = f"@{item['username']}" if item["username"] else "ندارد"
    action = "unban" if item["is_banned"] else "ban"
    label = "✅ رفع مسدودیت" if item["is_banned"] else "🚫 مسدود کردن"
    await message.reply_text(
        f"👤 کاربر {item['first_name'] or '-'}\n"
        f"شناسه: {item['telegram_id']}\nنام کاربری: {username}\n"
        f"موجودی کیف پول: {item['wallet_balance']:,} تومان\nوضعیت: {status}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=f"{action}_{user_id}")],
            [InlineKeyboardButton("🔙 فهرست کاربران", callback_data="admin_users")],
        ]),
    )


async def show_admin_stats(message):
    stats = get_dashboard_statistics()
    await message.reply_text(
        "📊 آمار VitoPlus\n\n"
        f"👥 کاربران: {stats['users']['total']} (مسدود: {stats['users']['banned']})\n"
        f"📦 محصولات: {stats['products']['total']} (فعال: {stats['products']['active']})\n"
        f"🧩 موجودی: {stats['products']['total_stock']}\n"
        f"🛍 سفارش‌ها: {stats['orders']['total']}\n"
        f"✅ تکمیل‌شده: {stats['orders']['completed']}\n"
        f"⌛ در انتظار: {stats['orders']['pending']}\n"
        f"⭐ خریدهای Stars: {stats['stars']['total']}\n"
        f"💰 ورودی کیف پول: {stats['transactions']['positive_amount']:,} تومان\n"
        f"💸 خروجی کیف پول: {stats['transactions']['negative_amount']:,} تومان",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")
        ]]),
    )


async def show_admin_list(message):
    admins = get_active_admins()
    if not admins:
        await message.reply_text("مدیر فعالی ثبت نشده است.")
        return
    lines = ["👮 مدیران فعال VitoPlus:\n"]
    for item in admins:
        lines.append(f"🆔 {item['telegram_id']} | نقش: {item['role']}")
    await message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")
        ]]),
    )


# ----------------------------- Callback router -----------------------------

async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return

    data = query.data or ""

    # This handler answers its own callback query.
    if data.startswith("buy_stars_"):
        await buy_with_stars(update, context)
        return

    await query.answer()

    if data == "buy":
        context.user_data.pop("support_waiting", None)
        await show_products(query)
    elif data.startswith("product_"):
        try:
            product_id = int(data.rsplit("_", 1)[1])
        except (TypeError, ValueError):
            await query.edit_message_text("شناسه محصول معتبر نیست.")
            return
        await show_product(query, product_id)
    elif data == "main":
        context.user_data.clear()
        await query.edit_message_text(
            "🏠 منوی اصلی VitoPlus\n\nیکی از بخش‌های زیر رو انتخاب کن:",
            reply_markup=main_menu(),
        )
    elif data == "wallet":
        await show_wallet(update, context)
    elif data == "account":
        await account(update, context)
    elif data == "orders":
        await user_orders(update, context)
    elif data == "transactions":
        await transactions(update, context)
    elif data == "referrals":
        await referrals(update, context)
    elif data == "support":
        context.user_data["support_waiting"] = True
        await support(update, context)
    elif data == "guide":
        await query.message.reply_text(
            "📖 راهنمای VitoPlus\n\n"
            "۱. از بخش خرید سرویس، محصولات موجود را ببین.\n"
            "۲. محصول را انتخاب کن.\n"
            "۳. اگر پرداخت Stars فعال باشد، دکمه خرید نمایش داده می‌شود.\n"
            "۴. پس از پرداخت موفق، کانفیگ در همین گفت‌وگو ارسال می‌شود.\n"
            "۵. سفارش‌ها و تراکنش‌ها از منوی اصلی قابل مشاهده‌اند.",
            reply_markup=main_menu(),
        )
    elif data == "cancel":
        context.user_data.clear()
        await query.message.reply_text("عملیات لغو شد.", reply_markup=main_menu())

    # Admin-only routes
    elif data in {
        "admin", "admin_users", "admin_orders", "admin_logs",
        "admin_products", "admin_stats", "admin_manage",
    } or data.startswith(("admin_product_", "admin_user_", "edit_price_",
                          "edit_stock_", "toggle_product_", "ban_", "unban_")):
        if not is_admin(user.id):
            await query.message.reply_text("⛔ دسترسی غیرمجاز.")
            return

        if data == "admin":
            await admin_panel(update, context)
        elif data == "admin_users":
            await show_admin_users(query.message)
        elif data == "admin_orders":
            await admin_orders(update, context)
        elif data == "admin_logs":
            await admin_logs(update, context)
        elif data == "admin_products":
            await show_admin_products(query.message)
        elif data == "admin_stats":
            await show_admin_stats(query.message)
        elif data == "admin_manage":
            await show_admin_list(query.message)
        elif data.startswith("admin_product_"):
            await show_admin_product(query.message, int(data.rsplit("_", 1)[1]))
        elif data.startswith("admin_user_"):
            await show_admin_user(query.message, int(data.rsplit("_", 1)[1]))
        elif data.startswith("edit_price_"):
            product_id = int(data.rsplit("_", 1)[1])
            context.user_data.clear()
            context.user_data["admin_input"] = "price"
            context.user_data["admin_product_id"] = product_id
            await query.message.reply_text("قیمت جدید را به تومان و فقط به‌صورت عدد بفرست. برای لغو /cancel را بزن.")
        elif data.startswith("edit_stock_"):
            product_id = int(data.rsplit("_", 1)[1])
            product = get_product_details(product_id)
            if not product:
                await query.message.reply_text("محصول پیدا نشد.")
            elif product["product_type"] == "digital":
                await query.message.reply_text(
                    "موجودی محصول دیجیتال از تعداد کانفیگ‌های ثبت‌شده محاسبه می‌شود؛ "
                    "ویرایش عددی موجودی برای آن مجاز نیست."
                )
            else:
                context.user_data.clear()
                context.user_data["admin_input"] = "stock"
                context.user_data["admin_product_id"] = product_id
                await query.message.reply_text("موجودی جدید را به‌صورت عدد صحیح بفرست. برای لغو /cancel را بزن.")
        elif data.startswith("toggle_product_"):
            product_id = int(data.rsplit("_", 1)[1])
            product = get_product_details(product_id)
            if product:
                set_product_active(product_id, not bool(product["is_active"]))
                audit(user.id, "toggle_product", f"product_id={product_id}")
                await show_admin_product(query.message, product_id)
        elif data.startswith("ban_"):
            target_id = int(data.rsplit("_", 1)[1])
            if set_user_ban(target_id, True):
                audit(user.id, "ban_user", f"user_id={target_id}")
            await show_admin_user(query.message, target_id)
        elif data.startswith("unban_"):
            target_id = int(data.rsplit("_", 1)[1])
            if set_user_ban(target_id, False):
                audit(user.id, "unban_user", f"user_id={target_id}")
            await show_admin_user(query.message, target_id)
    else:
        await query.message.reply_text(
            "این گزینه هنوز فعال نشده است.", reply_markup=main_menu()
        )


# ----------------------------- Incoming messages -----------------------------

async def incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    if context.user_data.get("admin_input"):
        if not is_admin(user.id):
            context.user_data.clear()
            await message.reply_text("⛔ دسترسی غیرمجاز.")
            return
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await message.reply_text("فقط عدد صحیح و مثبت بفرست. برای لغو /cancel را بزن.")
            return
        value = int(raw)
        if value <= 0:
            await message.reply_text("عدد باید بیشتر از صفر باشد.")
            return

        action = context.user_data.get("admin_input")
        product_id = context.user_data.get("admin_product_id")
        if action == "price":
            ok, result = update_product(product_id, price=value)
            if ok:
                audit(user.id, "edit_product_price", f"product_id={product_id}; price={value}")
                context.user_data.clear()
                await message.reply_text("✅ قیمت محصول به‌روزرسانی شد.")
                await show_admin_product(message, product_id)
            else:
                await message.reply_text(str(result))
        elif action == "stock":
            ok = set_product_stock(product_id, value)
            if ok:
                audit(user.id, "edit_product_stock", f"product_id={product_id}; stock={value}")
                context.user_data.clear()
                await message.reply_text("✅ موجودی محصول به‌روزرسانی شد.")
                await show_admin_product(message, product_id)
            else:
                await message.reply_text("❌ تغییر موجودی انجام نشد.")
        return

    if context.user_data.get("support_waiting"):
        await handle_support_message(update, context)
        return

    if message.text:
        await message.reply_text(
            "برای شروع از /start استفاده کن یا یکی از گزینه‌های منو رو انتخاب کن.",
            reply_markup=main_menu(),
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    if error is not None:
        logger.error(
            "Unhandled exception while processing update: %s",
            error,
            exc_info=(type(error), error, error.__traceback__),
        )


# ----------------------------- Application startup -----------------------------

def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN پیدا نشد. آن را در فایل .env یا متغیرهای محیطی تنظیم کن."
        )

    initialize_database()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment)
    )
    application.add_handler(CallbackQueryHandler(route_callback))
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
            incoming_message,
        )
    )
    application.add_error_handler(error_handler)
    return application


def main():
    application = build_application()
    logger.info("VitoPlus is starting...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
